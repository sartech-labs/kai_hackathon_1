import json
import logging
import re
from typing import Dict, TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from ..runtime.inventory import InventoryManager


logger = logging.getLogger(__name__)


class LLMProductionAgent:
    """LLM agent responsible for manufacturing capacity and schedule feasibility."""

    def __init__(self, llm: ChatOpenAI, inventory_manager: 'InventoryManager'):
        self.llm = llm
        self.inventory_manager = inventory_manager
        self.name = 'Production Agent'
        self.prompt = ChatPromptTemplate.from_template(
            """
You are a Production Agent responsible for manufacturing planning and schedule feasibility.

Task: Analyze whether production can meet requested quantity and timeline.

Order Details:
- Product SKU: {product_sku}
- Quantity: {quantity}
- Requested Delivery Days: {requested_delivery_days}
- Priority: {priority}

Operational Baseline:
- Weekly Capacity: {weekly_capacity}
- Standard Lead Time: {standard_lead_time}
- Max Overtime Hours/Day: {max_overtime}
- Working Days/Week: {working_days}

Provide JSON with keys:
can_proceed, production_days, overtime_hours, reasoning, confidence
"""
        )

    def invoke(self, order: dict) -> Dict:
        requested_days = int(order.get('requested_delivery_days') or 18)
        quantity = int(order.get('quantity') or 0)
        policy = self.inventory_manager.production_policy
        prompt_value = self.prompt.format(
            product_sku=order.get('product_sku'),
            quantity=quantity,
            requested_delivery_days=requested_days,
            priority=order.get('priority', 'normal'),
            weekly_capacity=policy.get('weekly_capacity', 4000),
            standard_lead_time=policy.get('standard_lead_time_days', 22),
            max_overtime=policy.get('max_overtime_hours_per_day', 4),
            working_days=policy.get('working_days_per_week', 5),
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            response_text = response.content
            logger.info('[%s] Analysis: %s...', self.name, response_text[:200])

            analysis = self._extract_json_or_parse(response_text, quantity, requested_days)
            return {
                'agent': self.name,
                'can_proceed': bool(analysis.get('can_proceed', True)),
                'production_days': int(analysis.get('production_days', requested_days)),
                'overtime_hours': int(analysis.get('overtime_hours', 0)),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.8)),
            }
        except Exception as exc:
            logger.error('[%s] Error: %s', self.name, str(exc))
            fallback = self._fallback(quantity, requested_days)
            fallback['reasoning'] = f"Error in analysis: {str(exc)}"
            fallback['analysis'] = str(exc)
            return fallback

    def _extract_json_or_parse(self, response_text: str, quantity: int, requested_days: int) -> Dict:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return self._fallback(quantity, requested_days)

    def _fallback(self, quantity: int, requested_days: int) -> Dict:
        policy = self.inventory_manager.production_policy
        weekly_capacity = int(policy.get('weekly_capacity', 4000))
        working_days_per_week = int(policy.get('working_days_per_week', 5))
        max_planning_weeks = int(policy.get('max_planning_weeks', 4))
        max_overtime_per_day = int(policy.get('max_overtime_hours_per_day', 4))
        estimated_weeks = max(1, quantity / max(1, weekly_capacity))
        production_days = max(5, int(round(estimated_weeks * working_days_per_week)))
        can_proceed = quantity <= weekly_capacity * max_planning_weeks
        overtime_hours = max_overtime_per_day if requested_days < production_days else 2
        return {
            'can_proceed': can_proceed,
            'production_days': production_days,
            'overtime_hours': overtime_hours,
            'reasoning': 'Fallback production planning used from baseline capacity.',
            'confidence': 0.82 if can_proceed else 0.55,
        }
