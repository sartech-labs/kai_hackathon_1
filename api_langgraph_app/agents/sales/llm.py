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


class LLMSalesAgent:
    """LLM agent responsible for customer acceptability and final commercial sign-off."""

    def __init__(self, llm: ChatOpenAI, inventory_manager: 'InventoryManager'):
        self.llm = llm
        self.inventory_manager = inventory_manager
        self.name = 'Sales Agent'
        self.prompt = ChatPromptTemplate.from_template(
            """
You are a Sales Agent responsible for customer-acceptable terms and relationship management.

Inputs:
- Customer: {customer}
- Customer Tier: {customer_tier}
- Relationship Years: {relationship_years}
- Annual Volume: {annual_volume}
- Requested Price: {requested_price}
- Requested Delivery Days: {requested_days}
- Proposed Price: {proposed_price}
- Proposed Delivery Date: {delivery_date}

Provide JSON with keys:
can_proceed, agreed_price, reasoning, confidence
"""
        )

    def invoke(self, order: dict, finance_result: Dict, logistics_result: Dict) -> Dict:
        requested_price = float(order.get('requested_price') or 10.0)
        proposed_price = float(finance_result.get('final_price') or requested_price)
        customer_profile = self.inventory_manager.get_customer_profile(order.get('customer', ''))

        prompt_value = self.prompt.format(
            customer=order.get('customer', 'Acme Corp'),
            customer_tier=customer_profile.get('tier', 'standard'),
            relationship_years=customer_profile.get('relationship_years', 1),
            annual_volume=customer_profile.get('annual_volume', 25000),
            requested_price=requested_price,
            requested_days=int(order.get('requested_delivery_days') or 18),
            proposed_price=proposed_price,
            delivery_date=logistics_result.get('delivery_date', ''),
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            response_text = response.content
            logger.info('[%s] Analysis: %s...', self.name, response_text[:200])

            analysis = self._extract_json_or_parse(response_text, requested_price, proposed_price, customer_profile)
            return {
                'agent': self.name,
                'can_proceed': bool(analysis.get('can_proceed', True)),
                'agreed_price': float(analysis.get('agreed_price', proposed_price)),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.82)),
            }
        except Exception as exc:
            logger.error('[%s] Error: %s', self.name, str(exc))
            fallback = self._fallback(requested_price, proposed_price, customer_profile)
            fallback['reasoning'] = f"Error in analysis: {str(exc)}"
            fallback['analysis'] = str(exc)
            return fallback

    def _extract_json_or_parse(
        self,
        response_text: str,
        requested_price: float,
        proposed_price: float,
        customer_profile: Dict,
    ) -> Dict:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return self._fallback(requested_price, proposed_price, customer_profile)

    def _fallback(self, requested_price: float, proposed_price: float, customer_profile: Dict) -> Dict:
        max_acceptable = requested_price * float(customer_profile.get('max_price_uplift', 0.20))
        max_acceptable = max_acceptable + requested_price
        can_proceed = proposed_price <= max_acceptable
        return {
            'can_proceed': can_proceed,
            'agreed_price': proposed_price if can_proceed else max_acceptable,
            'reasoning': 'Fallback customer acceptance model applied.',
            'confidence': 0.8 if can_proceed else 0.6,
        }
