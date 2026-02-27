import json
import logging
import re
from typing import Dict, TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..runtime.inventory import InventoryManager


class LLMFinanceAgent:
    """LLM agent responsible for price, margin, and final deal economics."""

    def __init__(self, llm: ChatOpenAI, inventory_manager: 'InventoryManager'):
        self.llm = llm
        self.inventory_manager = inventory_manager
        self.name = 'Finance Agent'
        self.prompt = ChatPromptTemplate.from_template(
            """
You are a Finance Agent responsible for final pricing and margin feasibility.

Inputs:
- Quantity: {quantity}
- Requested Price: {requested_price}
- Priority: {priority}
- Material Cost Estimate: {material_cost}
- Shipping Cost Estimate: {shipping_cost}
- Production Overtime Hours: {overtime_hours}

Policy:
- Margin floor: {margin_floor}
- Target margin: {target_margin}
- Rush surcharge rate: {rush_surcharge_rate}

Provide JSON with keys:
can_proceed, discount_rate, final_price, total_deal_value, margin, reasoning, confidence
"""
        )

    def invoke(self, order: dict, procurement_result: Dict, production_result: Dict, logistics_result: Dict) -> Dict:
        quantity = max(1, int(order.get('quantity') or 1))
        requested_price = float(order.get('requested_price') or 10.0)
        material_cost = float(procurement_result.get('total_cost') or 0.0)
        shipping_cost = float(logistics_result.get('shipping_cost') or 0.0)
        overtime_hours = int(production_result.get('overtime_hours') or 0)

        prompt_value = self.prompt.format(
            quantity=quantity,
            requested_price=requested_price,
            priority=order.get('priority', 'normal'),
            material_cost=material_cost,
            shipping_cost=shipping_cost,
            overtime_hours=overtime_hours,
            margin_floor=self.inventory_manager.finance_policy.get('margin_floor', 0.15),
            target_margin=self.inventory_manager.finance_policy.get('target_margin', 0.22),
            rush_surcharge_rate=self.inventory_manager.finance_policy.get('rush_surcharge_rate', 0.12),
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            response_text = response.content
            logger.info('[%s] Analysis: %s...', self.name, response_text[:200])

            analysis = self._extract_json_or_parse(response_text, order, procurement_result, production_result, logistics_result)
            quantity_default = requested_price * quantity
            return {
                'agent': self.name,
                'can_proceed': self._as_bool(analysis.get('can_proceed', True)),
                'discount_rate': self._as_float(analysis.get('discount_rate'), 0.0),
                'final_price': self._as_float(analysis.get('final_price'), requested_price),
                'total_deal_value': self._as_float(analysis.get('total_deal_value'), quantity_default),
                'margin': self._as_float(
                    analysis.get('margin'),
                    float(self.inventory_manager.finance_policy.get('target_margin', 0.22)),
                ),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': self._as_float(analysis.get('confidence'), 0.82),
            }
        except Exception as exc:
            logger.error('[%s] Error: %s', self.name, str(exc))
            fallback = self._fallback(order, procurement_result, production_result, logistics_result)
            fallback['reasoning'] = f"Error in analysis: {str(exc)}"
            fallback['analysis'] = str(exc)
            return fallback

    def _extract_json_or_parse(
        self,
        response_text: str,
        order: dict,
        procurement_result: Dict,
        production_result: Dict,
        logistics_result: Dict,
    ) -> Dict:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return self._fallback(order, procurement_result, production_result, logistics_result)

    def _fallback(self, order: dict, procurement_result: Dict, production_result: Dict, logistics_result: Dict) -> Dict:
        policy = self.inventory_manager.finance_policy
        production_policy = self.inventory_manager.production_policy
        quantity = max(1, int(order.get('quantity') or 1))
        base_cost_per_unit = float(policy.get('base_cost_per_unit', 8.5))
        material_cost_total = float(procurement_result.get('total_cost') or (base_cost_per_unit * quantity))
        shipping_total = float(logistics_result.get('shipping_cost') or 0.0)
        overtime_cost_total = float(production_result.get('overtime_hours') or 0) * float(
            production_policy.get('overtime_cost_per_hour', 45.0)
        )
        unit_cost = (material_cost_total + shipping_total + overtime_cost_total) / quantity

        discount_rate = float(self.inventory_manager.get_volume_discount_rate(quantity))
        margin = float(policy.get('target_margin', 0.22))
        if str(order.get('priority', 'normal')).lower() in {'rush', 'expedited', 'critical'}:
            unit_cost = unit_cost * (1 + float(policy.get('rush_surcharge_rate', 0.12)))

        final_price = round((unit_cost * (1 + margin)) * (1 - discount_rate), 2)
        total_deal_value = round(final_price * quantity, 2)

        return {
            'can_proceed': margin >= float(policy.get('margin_floor', 0.15)),
            'discount_rate': discount_rate,
            'final_price': final_price,
            'total_deal_value': total_deal_value,
            'margin': margin,
            'reasoning': 'Fallback financial model applied from baseline constants.',
            'confidence': 0.84,
        }

    def _as_float(self, value, default: float) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)

        raw = str(value).strip().lower().replace('%', '').replace('$', '').replace(',', '')
        named = {'low': 0.15, 'medium': 0.20, 'high': 0.25}
        if raw in named:
            return named[raw]
        try:
            return float(raw)
        except ValueError:
            return default

    def _as_bool(self, value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        raw = str(value).strip().lower()
        return raw in {'1', 'true', 'yes', 'approved', 'ok'}
