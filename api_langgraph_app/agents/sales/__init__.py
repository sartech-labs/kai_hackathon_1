
from langchain_core.messages import HumanMessage

from .profile import AGENT_PROFILE, get_description, get_operational_parameters
from .tools import TOOLS
from .llm import LLMSalesAgent as _BaseLLMSalesAgent


class LLMSalesAgent(_BaseLLMSalesAgent):
    def invoke(self, order, finance_result, logistics_result):
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
            analysis = self._extract_json_or_parse(response_text, requested_price, proposed_price, customer_profile)
            fallback = self._fallback(requested_price, proposed_price, customer_profile)
            return {
                'agent': self.name,
                'can_proceed': self._as_bool(analysis.get('can_proceed'), fallback['can_proceed']),
                'agreed_price': self._as_float(analysis.get('agreed_price'), fallback['agreed_price']),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': self._as_float(analysis.get('confidence'), fallback['confidence']),
            }
        except Exception as exc:
            fallback = self._fallback(requested_price, proposed_price, customer_profile)
            fallback['reasoning'] = f"Error in analysis: {str(exc)}"
            fallback['analysis'] = str(exc)
            return fallback

    def _as_float(self, value, default):
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

    def _as_bool(self, value, default):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        raw = str(value).strip().lower()
        if raw in {'1', 'true', 'yes', 'approved', 'ok'}:
            return True
        if raw in {'0', 'false', 'no', 'rejected', 'blocked'}:
            return False
        return default
