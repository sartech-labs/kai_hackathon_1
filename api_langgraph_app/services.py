import json
import logging
import os
import time
from datetime import datetime

from .agents import AGENT_IDS
from .agents.runtime import OrderRequest, build_mock_process_order_response
from .constants import BASELINE
from . import state

logger = logging.getLogger(__name__)
MIN_CONSENSUS_CONFIDENCE = float(os.getenv('MIN_CONSENSUS_CONFIDENCE', '0.70'))


def safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_confidence(value, default=0.0):
    raw = safe_float(value, default)
    if raw > 1.0:
        raw = raw / 100.0
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw


def stabilize_agent_confidence(agent_response, fallback=0.78):
    normalized = normalize_confidence(agent_response.get('confidence', fallback), fallback)
    if bool(agent_response.get('can_proceed', False)) and normalized < 0.70:
        normalized = fallback
    agent_response['confidence'] = normalized
    return agent_response


def normalize_priority(priority):
    normalized = str(priority or 'standard').lower()
    if normalized in ['rush', 'critical', 'expedited']:
        return 'expedited'
    return 'normal'


def build_synk_order(payload):
    timestamp_suffix = str(int(time.time() * 1000))[-3:]
    return {
        'id': payload.get('id') or payload.get('order_id') or f'ORD-RUSH-{timestamp_suffix}',
        'customer': payload.get('customer', 'Acme Corp'),
        'product': payload.get('product') or payload.get('product_sku', 'PMP-STD-100'),
        'quantity': safe_int(payload.get('quantity'), 5000),
        'requestedPrice': safe_float(payload.get('requestedPrice', payload.get('requested_price')), 10.0),
        'requestedDeliveryDays': safe_int(payload.get('requestedDeliveryDays', payload.get('requested_delivery_days')), 18),
        'priority': str(payload.get('priority', 'rush')).lower(),
    }


def resolve_customer_location(payload):
    explicit_location = payload.get('customer_location')
    if explicit_location:
        return explicit_location

    customer = str(payload.get('customer', '')).lower()
    if 'local' in customer:
        return 'local city'
    if 'regional' in customer:
        return 'regional state'
    return 'national'


def run_process_order_for_synk(order, payload):
    order_request = OrderRequest(
        order_id=order['id'],
        product_sku=order['product'],
        quantity=max(1, safe_int(order['quantity'], 1)),
        customer_location=resolve_customer_location(payload),
        priority=normalize_priority(order.get('priority')),
        customer=order.get('customer', 'Acme Corp'),
        requested_price=safe_float(order.get('requestedPrice'), 10.0),
        requested_delivery_days=safe_int(order.get('requestedDeliveryDays'), 18),
    )

    use_mock_process_order = str(os.getenv('BACKEND_USE_MOCK_PROCESS_ORDER', 'true')).strip().lower() in {
        '1',
        'true',
        'yes',
        'on',
    }

    if use_mock_process_order:
        logger.info(
            'process_order running in mock mode. live_agent_pipeline_enabled=%s',
            all(
                [
                    state.procurement_agent is not None,
                    state.production_agent is not None,
                    state.logistics_agent is not None,
                    state.finance_agent is not None,
                    state.sales_agent is not None,
                    state.inventory_manager is not None,
                ]
            ),
        )
        if all(
            [
                state.procurement_agent is not None,
                state.production_agent is not None,
                state.logistics_agent is not None,
                state.finance_agent is not None,
                state.sales_agent is not None,
                state.inventory_manager is not None,
            ]
        ):
            response = run_live_agent_pipeline(order_request)
            return response, (
                'Using live multi-agent pipeline while BACKEND_USE_MOCK_PROCESS_ORDER=true '
                '(manager disabled, agent-by-agent execution enabled).'
            )

        response = build_mock_process_order_response(order_request)
        return response, 'Using mock process_order response (live agent pipeline unavailable).'

    if state.manager is None:
        response = build_mock_process_order_response(order_request)
        return response, 'LangGraph manager unavailable; using mock process_order response.'

    response = state.manager.process_order(order_request)
    return response, None


def _build_live_order_dict(order_request):
    return {
        'order_id': order_request.order_id,
        'product_sku': order_request.product_sku,
        'quantity': order_request.quantity,
        'customer_location': order_request.customer_location,
        'priority': order_request.priority,
        'customer': order_request.customer,
        'requested_price': order_request.requested_price,
        'requested_delivery_days': order_request.requested_delivery_days,
    }


def run_live_agent_pipeline(order_request):
    order = _build_live_order_dict(order_request)

    logger.info(
        'Invoking live agent pipeline for order=%s sku=%s qty=%s',
        order_request.order_id,
        order_request.product_sku,
        order_request.quantity,
    )

    procurement_result = state.procurement_agent.invoke(
        order,
        state.inventory_manager.inventory,
        state.inventory_manager.materials,
    )
    production_result = state.production_agent.invoke(order)
    logistics_result = state.logistics_agent.invoke(
        order,
        float(procurement_result.get('total_cost') or 0.0),
        int(production_result.get('production_days') or 14),
    )
    finance_result = state.finance_agent.invoke(order, procurement_result, production_result, logistics_result)
    sales_result = state.sales_agent.invoke(order, finance_result, logistics_result)

    agent_responses = {
        'procurement': stabilize_agent_confidence(procurement_result, 0.85),
        'production': stabilize_agent_confidence(production_result, 0.82),
        'logistics': stabilize_agent_confidence(logistics_result, 0.80),
        'finance': stabilize_agent_confidence(finance_result, 0.82),
        'sales': stabilize_agent_confidence(sales_result, 0.80),
    }

    all_can_proceed = all(bool(agent_responses[agent_id].get('can_proceed', False)) for agent_id in AGENT_IDS)
    avg_confidence = (
        sum(normalize_confidence(agent_responses[agent_id].get('confidence', 0.0), 0.0) for agent_id in AGENT_IDS)
        / len(AGENT_IDS)
    )
    consensus_reached = all_can_proceed and avg_confidence >= MIN_CONSENSUS_CONFIDENCE

    final_price = safe_float(
        sales_result.get('agreed_price', finance_result.get('final_price', order_request.requested_price)),
        order_request.requested_price,
    )
    total_deal_value = round(final_price * max(1, int(order_request.quantity)), 2)
    delivery_date = logistics_result.get('delivery_date', '')

    rejection_reason = None
    if not consensus_reached:
        for agent_id in AGENT_IDS:
            if not bool(agent_responses[agent_id].get('can_proceed', False)):
                rejection_reason = agent_responses[agent_id].get('reasoning')
                break
        if rejection_reason is None:
            rejection_reason = 'Consensus confidence threshold not met.'

    response = {
        'status': 'SUCCESS' if consensus_reached else 'FAILURE',
        'order_id': order_request.order_id,
        'product_sku': order_request.product_sku,
        'quantity': int(order_request.quantity),
        'customer_location': order_request.customer_location,
        'final_price': final_price,
        'total_deal_value': total_deal_value,
        'delivery_date': delivery_date,
        'cost_breakdown': {
            'discount_rate': safe_float(finance_result.get('discount_rate', 0.0), 0.0),
            'profit_margin': safe_float(finance_result.get('margin', 0.22), 0.22),
        },
        'consensus_reached': consensus_reached,
        'message': None if consensus_reached else rejection_reason,
        'agent_responses': agent_responses,
        'live_agents': AGENT_IDS,
        'mock_mode': False,
        'timestamp': datetime.utcnow().isoformat(),
    }

    logger.info(
        'Live agent pipeline completed for order=%s consensus=%s confidence=%.2f',
        order_request.order_id,
        consensus_reached,
        avg_confidence,
    )
    return response


def agent_status_and_approval(agent_id, round_number):
    if round_number == 1 and agent_id == 'finance':
        return 'objecting', False
    if round_number < 3:
        return 'proposing', True
    return 'agreed', True


def mock_agent_proposal(agent_id, order, round_number, previous_round=None):
    status, approved = agent_status_and_approval(agent_id, round_number)
    requested_price = safe_float(order.get('requestedPrice'), 10.0)
    requested_days = safe_int(order.get('requestedDeliveryDays'), 18)

    if round_number == 1:
        target_price = requested_price
        target_days = requested_days
        margin = 12.4
    elif round_number == 2:
        target_price = max(10.8, requested_price)
        target_days = requested_days + 1
        margin = 17.2
    else:
        target_price = max(10.8, requested_price)
        target_days = requested_days + 1
        margin = 20.6

    previous_round_ref = previous_round.get('round') if isinstance(previous_round, dict) else None
    reasoning = {
        'production': f"Capacity aligned for {order.get('quantity', 5000)} units in {target_days} days with controlled overtime.",
        'finance': f"Margin check at ${target_price:.2f}/unit -> {margin:.1f}% margin {'meets' if approved else 'below'} floor.",
        'logistics': f"Ground freight supports {target_days}-day commitment with reliable carrier availability.",
        'procurement': f"Supplier {BASELINE['primarySupplier']} confirms material reservation for requested quantity.",
        'sales': f"Strategic account posture supports negotiated terms at ${target_price:.2f}/unit.",
    }.get(agent_id, 'Agent analysis complete.')

    actions = [
        {
            'kind': 'tool_call',
            'label': f'{agent_id}_analyze()',
            'detail': f"Round {round_number} analysis started for order {order.get('id', 'ORD-RUSH-001')}.",
            'data': {'round': round_number, 'previous_round': previous_round_ref or 0},
        },
        {
            'kind': 'tool_result',
            'label': f'{agent_id}_result',
            'detail': f'Computed position at ${target_price:.2f} and {target_days} delivery days.',
            'data': {'price': target_price, 'delivery_days': target_days, 'margin': margin},
        },
        {
            'kind': 'objection' if not approved else 'agreement',
            'label': 'position',
            'detail': reasoning,
        },
    ]

    return {
        'agentId': agent_id,
        'round': round_number,
        'status': status,
        'reasoning': reasoning,
        'metrics': {
            'price': round(target_price, 2),
            'deliveryDays': target_days,
            'margin': round(margin, 1),
            'quantity': safe_int(order.get('quantity'), 5000),
        },
        'approved': approved,
        'actions': actions,
    }


def build_round_summary(order, round_number, previous_round=None):
    requested_price = safe_float(order.get('requestedPrice'), 10.0)
    requested_days = safe_int(order.get('requestedDeliveryDays'), 18)

    if round_number == 1:
        price = requested_price
        delivery_days = requested_days
        margin = 12.4
        overtime_hours = 12
        converged = False
    elif round_number == 2:
        price = max(10.8, requested_price)
        delivery_days = requested_days + 1
        margin = 17.2
        overtime_hours = 8
        converged = False
    else:
        price = max(10.8, requested_price)
        delivery_days = requested_days + 1
        margin = 20.6
        overtime_hours = 8
        converged = True

    proposals = [
        mock_agent_proposal(agent_id, order, round_number, previous_round)
        for agent_id in AGENT_IDS
    ]

    return {
        'round': round_number,
        'price': round(price, 2),
        'deliveryDays': delivery_days,
        'margin': margin,
        'shippingMode': 'ground',
        'overtimeHours': overtime_hours,
        'proposals': proposals,
        'converged': converged,
    }


def _status_for_procurement(approved, round_number):
    if approved:
        return 'agreed' if round_number >= 3 else 'proposing'
    return 'objecting'


def apply_live_agent_results_to_round(round_summary, process_response):
    """
    Override round proposals with live process_order agent outputs when available.
    """
    if not isinstance(process_response, dict):
        return round_summary

    live_agent_responses = process_response.get('agent_responses') or {}
    if not isinstance(live_agent_responses, dict):
        return round_summary

    proposals = list(round_summary.get('proposals') or [])
    all_live_approved = True
    live_found = False

    for index, proposal in enumerate(proposals):
        agent_id = proposal.get('agentId')
        live_result = live_agent_responses.get(agent_id)
        if not isinstance(live_result, dict):
            continue

        live_found = True
        approved = bool(live_result.get('can_proceed', False))
        round_number = safe_int(round_summary.get('round'), 1)
        quantity = safe_int(proposal.get('metrics', {}).get('quantity'), 0)
        delivery_days = safe_int(round_summary.get('deliveryDays'), 0)
        price = safe_float(proposal.get('metrics', {}).get('price'), 0)
        margin = safe_float(proposal.get('metrics', {}).get('margin'), 0)

        if agent_id == 'finance':
            price = safe_float(live_result.get('final_price'), price)
            margin_value = safe_float(live_result.get('margin'), margin)
            margin = margin_value * 100 if margin_value <= 1 else margin_value
        elif agent_id == 'sales':
            price = safe_float(live_result.get('agreed_price'), price)
        elif agent_id == 'production':
            delivery_days = safe_int(live_result.get('production_days'), delivery_days)
        elif agent_id == 'logistics':
            parsed_days = extract_delivery_days_from_process_response(
                {'delivery_date': live_result.get('delivery_date')}
            )
            if parsed_days is not None:
                delivery_days = parsed_days

        live_reason = live_result.get('reasoning') or live_result.get('llm_reasoning') or f'{agent_id} analysis completed.'
        actions = [
            {
                'kind': 'tool_call',
                'label': f'{agent_id}_live_analyze()',
                'detail': f'Live {agent_id} analysis executed for round {round_number}.',
                'data': {
                    'decision_source': live_result.get('decision_source', 'llm'),
                    'live': True,
                },
            },
            {
                'kind': 'agreement' if approved else 'objection',
                'label': f'{agent_id}_verdict',
                'detail': live_reason,
                'data': {
                    'can_proceed': approved,
                },
            },
        ]

        proposals[index] = {
            'agentId': agent_id,
            'round': round_number,
            'status': _status_for_procurement(approved, round_number),
            'reasoning': live_reason,
            'metrics': {
                'price': price,
                'deliveryDays': delivery_days,
                'margin': margin,
                'quantity': quantity,
            },
            'approved': approved,
            'actions': actions,
            'live': True,
        }

        if not approved:
            all_live_approved = False

    round_summary['proposals'] = proposals
    if live_found and not all_live_approved:
        round_summary['converged'] = False
    return round_summary


def extract_delivery_days_from_process_response(process_response):
    delivery_date = process_response.get('delivery_date')
    if not delivery_date:
        return None
    try:
        delivery_dt = datetime.strptime(delivery_date, '%Y-%m-%d').date()
        today = datetime.utcnow().date()
        return max(1, (delivery_dt - today).days)
    except ValueError:
        return None


def synthesize_consensus(order, rounds, process_response=None):
    final_round = rounds[-1]
    approved = bool(final_round.get('converged'))
    final_price = safe_float(final_round.get('price'), 10.8)
    final_delivery_days = safe_int(final_round.get('deliveryDays'), 19)
    final_margin = safe_float(final_round.get('margin'), 20.6)
    shipping_mode = final_round.get('shippingMode', 'ground')
    overtime_hours = safe_int(final_round.get('overtimeHours'), 8)
    confidence = 94 if approved else 62
    rejection_reason = None

    if process_response:
        approved = bool(process_response.get('consensus_reached', approved))
        final_price = safe_float(process_response.get('final_price'), final_price)
        profit_margin = process_response.get('cost_breakdown', {}).get('profit_margin')
        final_margin = round(safe_float(profit_margin, 0.25) * 100, 1)
        inferred_days = extract_delivery_days_from_process_response(process_response)
        if inferred_days is not None:
            final_delivery_days = inferred_days
        confidence = 90 if approved else 58
        if not approved:
            rejection_reason = (
                process_response.get('message')
                or (process_response.get('agent_responses', {}).get('procurement', {}) or {}).get('reasoning')
            )

    risk_score = 'Low' if final_margin >= 20 else ('Medium' if final_margin >= 15 else 'High')
    order_id = order.get('id', 'ORD-RUSH-001')
    quantity = safe_int(order.get('quantity'), 5000)
    product = order.get('product', 'PMP-STD-100')

    if approved:
        summary = (
            f'Order {order_id} APPROVED. {quantity} units of {product} at '
            f'${final_price:.2f}/unit, delivered in {final_delivery_days} days via '
            f'{shipping_mode} freight. Margin: {final_margin:.1f}%. '
            f'All agents reached consensus in {len(rounds)} rounds.'
        )
    else:
        if rejection_reason:
            summary = (
                f'Order {order_id} REJECTED. Reason: {rejection_reason} '
                f'(after {len(rounds)} rounds).'
            )
        else:
            summary = (
                f'Order {order_id} REJECTED. Unable to meet requested terms within '
                f'operational constraints after {len(rounds)} rounds.'
            )

    return {
        'approved': approved,
        'finalPrice': round(final_price, 2),
        'finalDeliveryDays': final_delivery_days,
        'finalMargin': round(final_margin, 1),
        'shippingMode': shipping_mode,
        'riskScore': risk_score,
        'confidence': confidence,
        'supplier': BASELINE['primarySupplier'],
        'overtimeHours': overtime_hours,
        'rejectionReason': rejection_reason,
        'summary': summary,
    }


def sse_event(event_type, data):
    return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"


def build_round_messages(round_number, id_counter):
    templates = {
        1: [
            ('orchestrator', 'all', 'directive', 'Broadcasting rush order to all agents. Begin independent analysis.'),
            ('production', 'orchestrator', 'proposal', 'Capacity check complete. Feasible with overtime allocation.'),
            ('finance', 'orchestrator', 'objection', 'Margin below floor at initial price; requesting surcharge.'),
            ('logistics', 'orchestrator', 'proposal', 'Ground mode selected; route and lead time are feasible.'),
            ('procurement', 'orchestrator', 'info', 'Primary supplier confirms material availability.'),
            ('sales', 'orchestrator', 'proposal', 'Strategic account constraints captured; negotiation buffer available.'),
        ],
        2: [
            ('orchestrator', 'all', 'directive', 'Round 2 negotiation: finance/sales align pricing, production/logistics refine schedule.'),
            ('finance', 'sales', 'proposal', 'Proposed revised price to satisfy margin threshold.'),
            ('sales', 'finance', 'counter', 'Counter-offer issued to preserve customer relationship.'),
            ('production', 'logistics', 'info', 'Adjusted production schedule lowers overtime burden.'),
            ('procurement', 'orchestrator', 'agreement', 'Material reservation locked with supplier.'),
        ],
        3: [
            ('orchestrator', 'all', 'directive', 'Round 3 final verification: confirm no blocking objections.'),
            ('production', 'orchestrator', 'agreement', 'Production schedule locked and approved.'),
            ('finance', 'orchestrator', 'agreement', 'Final margin check passed.'),
            ('logistics', 'orchestrator', 'agreement', 'Carrier booking finalized.'),
            ('procurement', 'orchestrator', 'agreement', 'Purchase order ready for execution.'),
            ('sales', 'orchestrator', 'agreement', 'Customer-ready terms finalized.'),
        ],
    }

    messages = []
    timestamp = int(time.time() * 1000)
    for from_agent, to_agent, msg_type, message in templates.get(round_number, []):
        id_counter += 1
        messages.append({
            'id': f'msg-{id_counter}',
            'from': from_agent,
            'to': to_agent,
            'round': round_number,
            'type': msg_type,
            'message': message,
            'timestamp': timestamp + id_counter,
        })
    return messages, id_counter


def get_agent_processing_delay(agent_id, round_number):
    """
    Return per-agent completion offset (seconds) for SSE simulation.
    Each value represents when that agent should finish relative to round start.
    """
    base_completion_offset = {
        'logistics': 2.0,
        'sales': 4.0,
        'production': 6.0,
        'procurement': 8.0,
        'finance': 10.0,
    }.get(agent_id, 5.0)

    # Slightly longer rounds as negotiation deepens.
    round_bump = 0.75 * max(0, round_number - 1)
    return base_completion_offset + round_bump
