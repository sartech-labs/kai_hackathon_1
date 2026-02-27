import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..runtime.inventory import InventoryManager


class LLMLogisticsAgent:
    """LLM agent responsible for shipping cost and ETA analysis."""

    def __init__(self, llm: ChatOpenAI, inventory_manager: 'InventoryManager'):
        self.llm = llm
        self.inventory_manager = inventory_manager
        self.name = 'Logistics Agent'
        self.prompt = ChatPromptTemplate.from_template(
            """
You are a Logistics Agent responsible for calculating shipping costs and delivery timelines.

Task: Analyze the following order request and provide:
1. Location type classification (local/regional/national/international)
2. Estimated shipping cost
3. Estimated delivery date
4. Any logistical concerns
5. Your confidence level (0.0-1.0)

Order Details:
- Product SKU: {product_sku}
- Quantity: {quantity}
- Customer Location: {customer_location}
- Priority: {priority}
- Material Cost: {material_cost}
- Planned Production Days: {production_days}

Provide your analysis in JSON format with keys: location_type, shipping_cost, delivery_date, reasoning, confidence
"""
        )

    def invoke(self, order: dict, material_cost: float, production_days: int) -> Dict:
        logger.info('[%s] Calculating logistics for %s', self.name, order['customer_location'])

        prompt_value = self.prompt.format(
            product_sku=order['product_sku'],
            quantity=order['quantity'],
            customer_location=order['customer_location'],
            priority=order.get('priority', 'normal'),
            material_cost=material_cost,
            production_days=production_days,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            response_text = response.content
            logger.info('[%s] Analysis: %s...', self.name, response_text[:200])

            analysis = self._extract_json_or_parse(response_text, order, production_days)
            delivery_date = self._sanitize_delivery_date(
                analysis.get('delivery_date'),
                order.get('priority'),
                production_days,
            )
            return {
                'agent': self.name,
                'can_proceed': True,
                'location_type': analysis.get('location_type', 'unknown'),
                'shipping_mode': analysis.get('shipping_mode', self.inventory_manager.logistics_policy.get('default_mode', 'ground')),
                'shipping_cost': float(analysis.get('shipping_cost', 50)),
                'delivery_date': delivery_date,
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.8)),
            }
        except Exception as exc:
            logger.error('[%s] Error: %s', self.name, str(exc))
            fallback = self._fallback(order, production_days)
            return {
                'agent': self.name,
                'can_proceed': bool(fallback.get('can_proceed', True)),
                'location_type': fallback.get('location_type', 'unknown'),
                'shipping_mode': fallback.get('shipping_mode', 'ground'),
                'shipping_cost': float(fallback.get('shipping_cost', 50.0)),
                'delivery_date': fallback.get('delivery_date', self._default_delivery_date(order.get('priority'), production_days)),
                'reasoning': f'Error in analysis: {str(exc)}',
                'analysis': str(exc),
                'confidence': float(fallback.get('confidence', 0.5)),
            }

    def _extract_json_or_parse(self, response_text: str, order: dict, production_days: int) -> Dict:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return self._parse_analysis(response_text, order, production_days)

    def _parse_analysis(self, text: str, order: dict, production_days: int) -> Dict:
        fallback = self._fallback(order, production_days)
        fallback['reasoning'] = text
        return fallback

    def _fallback(self, order: dict, production_days: int) -> Dict:
        quantity = int(order.get('quantity') or 0)
        requested_days = int(order.get('requested_delivery_days') or 18)
        location_profile = self.inventory_manager.get_location_profile(order.get('customer_location'))
        location_type = location_profile.get('type', 'national')

        shipping_modes = self.inventory_manager.logistics_policy.get('shipping_modes', {})
        default_mode = self.inventory_manager.logistics_policy.get('default_mode', 'ground')
        mode = default_mode
        if requested_days <= production_days + 1 and 'air' in shipping_modes:
            mode = 'air'
        elif requested_days <= production_days + 3 and 'express' in shipping_modes:
            mode = 'express'

        mode_cfg = shipping_modes.get(mode, shipping_modes.get(default_mode, {'cost_per_unit': 0.3, 'transit_days': 5}))
        transit_days = int(mode_cfg.get('transit_days', 5))
        shipping_cost = round(float(mode_cfg.get('cost_per_unit', 0.3)) * quantity, 2)
        total_days = max(1, production_days + transit_days)
        delivery_date = (datetime.utcnow().date() + timedelta(days=total_days)).strftime('%Y-%m-%d')

        return {
            'can_proceed': True,
            'location_type': location_type,
            'shipping_mode': mode,
            'shipping_cost': shipping_cost,
            'delivery_date': delivery_date,
            'reasoning': (
                f'Fallback logistics selected {mode} for {location_type} delivery. '
                f'Transit {transit_days}d after production.'
            ),
            'confidence': 0.8,
        }

    def _default_delivery_date(self, priority: str = 'normal', production_days: int = 10) -> str:
        days = production_days + (2 if priority == 'expedited' else 5)
        return (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

    def _sanitize_delivery_date(self, raw_date, priority: str, production_days: int) -> str:
        if isinstance(raw_date, str):
            try:
                parsed = datetime.strptime(raw_date, '%Y-%m-%d').date()
                if parsed >= datetime.utcnow().date():
                    return raw_date
            except ValueError:
                pass
        return self._default_delivery_date(priority, production_days)
