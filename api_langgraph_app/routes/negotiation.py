import json
import time
from urllib.parse import unquote

from flask import Blueprint, Response, jsonify, request, stream_with_context

from .. import state
from ..services import (
    apply_live_agent_results_to_round,
    build_round_messages,
    build_round_summary,
    build_synk_order,
    get_agent_processing_delay,
    run_process_order_for_synk,
    safe_int,
    sse_event,
    synthesize_consensus,
)


negotiation_bp = Blueprint('negotiation_api', __name__, url_prefix='/api')


@negotiation_bp.post('/rounds')
def execute_round():
    body = request.get_json(silent=True) or {}
    if 'order' not in body:
        return jsonify({'error': "Missing 'order' in request body"}), 400

    order = body['order']
    round_number = safe_int(body.get('round'), 1)
    if round_number < 1 or round_number > 3:
        return jsonify({'error': 'Round must be between 1 and 3'}), 400

    previous_round = body.get('previousRound')
    round_summary = build_round_summary(order, round_number, previous_round)

    return jsonify({
        'round': round_summary['round'],
        'converged': round_summary['converged'],
        'summary': round_summary,
        'agentProposals': [
            {
                'agentId': proposal['agentId'],
                'status': proposal['status'],
                'approved': proposal['approved'],
                'reasoning': proposal['reasoning'],
                'metrics': proposal['metrics'],
                'actions': proposal['actions'],
            }
            for proposal in round_summary['proposals']
        ],
    })


@negotiation_bp.post('/consensus')
def consensus():
    body = request.get_json(silent=True) or {}
    if 'order' not in body or 'rounds' not in body:
        return jsonify({'error': "Missing 'order' or 'rounds' in request body"}), 400

    rounds = body['rounds']
    if not rounds:
        return jsonify({'error': 'At least one round is required to synthesize consensus'}), 400

    consensus_payload = synthesize_consensus(body['order'], rounds)
    final_round = rounds[-1]

    return jsonify({
        'consensus': consensus_payload,
        'metadata': {
            'totalRounds': len(rounds),
            'finalRound': final_round.get('round'),
            'allConverged': final_round.get('converged', False),
            'agentApprovals': [
                {
                    'agentId': proposal.get('agentId'),
                    'approved': proposal.get('approved'),
                    'status': proposal.get('status'),
                }
                for proposal in final_round.get('proposals', [])
            ],
        },
    })


@negotiation_bp.get('/orchestrate')
def orchestrate():
    order_json = request.args.get('order')
    if not order_json:
        return Response('Missing order parameter', status=400)

    try:
        order_payload = json.loads(unquote(order_json))
        if not isinstance(order_payload, dict):
            raise ValueError('Order must be a JSON object')
    except Exception as exc:
        return Response(f'Invalid order parameter: {str(exc)}', status=400)

    order = build_synk_order(order_payload)

    try:
        process_response, process_warning = run_process_order_for_synk(order, order_payload)
    except Exception as process_err:
        state.logger.error('/api/orchestrate process_order failed: %s', process_err)
        process_response = None
        process_warning = f'process_order failed: {str(process_err)}'

    @stream_with_context
    def generate():
        rounds = []
        message_counter = 0

        yield sse_event('phase_change', {'phase': 'order-broadcast'})
        if process_warning:
            yield sse_event('callback_message', {'message': f'Backend warning: {process_warning}'})
        time.sleep(0.4)

        for round_number in [1, 2, 3]:
            yield sse_event('phase_change', {'phase': f'round-{round_number}'})
            time.sleep(0.2)

            previous_round = rounds[-1] if rounds else None
            round_summary = build_round_summary(order, round_number, previous_round)
            round_summary = apply_live_agent_results_to_round(round_summary, process_response)
            rounds.append(round_summary)

            round_messages, message_counter = build_round_messages(round_number, message_counter)
            for message in round_messages:
                yield sse_event('agent_message', {'agentMessage': message})
                time.sleep(0.15)

            # Emit agent updates by completion time so each agent appears at
            # clearly different moments even if all started simultaneously.
            updates_with_offsets = []
            for proposal in round_summary['proposals']:
                completion_offset = get_agent_processing_delay(proposal['agentId'], round_number)
                updates_with_offsets.append((completion_offset, proposal))

            updates_with_offsets.sort(key=lambda item: item[0])
            previous_offset = 0.0
            for completion_offset, proposal in updates_with_offsets:
                wait_for = max(0.0, completion_offset - previous_offset)
                time.sleep(wait_for)
                yield sse_event('agent_update', {'agentId': proposal['agentId'], 'proposal': proposal})
                previous_offset = completion_offset

            yield sse_event('round_complete', {'roundSummary': round_summary})
            time.sleep(0.25)

        yield sse_event('phase_change', {'phase': 'consensus'})
        time.sleep(0.2)

        consensus_payload = synthesize_consensus(order, rounds, process_response)
        yield sse_event('consensus_reached', {'consensus': consensus_payload})
        time.sleep(0.25)

        yield sse_event('phase_change', {'phase': 'callback'})
        yield sse_event('callback_start', {'message': f"Calling back {order.get('customer', 'customer')}..."})
        time.sleep(0.2)

        if consensus_payload['approved']:
            callback_messages = [
                f"Hello {order.get('customer', 'customer')}, your rush order is approved.",
                f"Final quote is ${consensus_payload['finalPrice']:.2f}/unit with {consensus_payload['finalDeliveryDays']}-day delivery.",
                'We will send the formal confirmation and schedule details shortly.',
            ]
        else:
            callback_messages = [
                (
                    f"Hello {order.get('customer', 'customer')}, this is SYNK Agent calling with an update. "
                    "We could not approve the order under requested terms."
                ),
                consensus_payload.get('rejectionReason') or consensus_payload.get('summary'),
                'We will share revised options with feasible quantity/price/delivery shortly.',
            ]

        for callback_msg in callback_messages:
            yield sse_event('callback_message', {'message': callback_msg})
            time.sleep(0.2)

        yield sse_event('phase_change', {'phase': 'done'})
        yield sse_event('done', {})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    )
