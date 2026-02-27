
from langchain_core.messages import HumanMessage

from .profile import AGENT_PROFILE, get_description, get_operational_parameters
from .tools import TOOLS
from .llm import LLMLogisticsAgent as _BaseLLMLogisticsAgent


class LLMLogisticsAgent(_BaseLLMLogisticsAgent):
    def invoke(self, order, material_cost, production_days):
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
            analysis = self._extract_json_or_parse(response_text, order, production_days)
            fallback = self._fallback(order, production_days)
            delivery_date = self._sanitize_delivery_date(
                analysis.get('delivery_date'),
                order.get('priority'),
                production_days,
            )
            return {
                'agent': self.name,
                'can_proceed': self._as_bool(analysis.get('can_proceed'), fallback.get('can_proceed', True)),
                'location_type': str(analysis.get('location_type', fallback.get('location_type', 'unknown'))),
                'shipping_mode': str(
                    analysis.get(
                        'shipping_mode',
                        fallback.get('shipping_mode', self.inventory_manager.logistics_policy.get('default_mode', 'ground')),
                    )
                ),
                'shipping_cost': self._as_float(analysis.get('shipping_cost'), float(fallback.get('shipping_cost', 50.0))),
                'delivery_date': delivery_date,
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': self._as_float(analysis.get('confidence'), float(fallback.get('confidence', 0.8))),
            }
        except Exception as exc:
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
