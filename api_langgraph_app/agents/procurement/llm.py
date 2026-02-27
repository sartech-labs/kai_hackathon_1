import json
import logging
import re
from typing import Dict, List, TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from ..runtime.inventory import InventoryManager


logger = logging.getLogger(__name__)


class LLMProcurementAgent:
    """LLM agent responsible for availability and material cost checks."""

    def __init__(self, llm: ChatOpenAI, inventory_manager: 'InventoryManager'):
        self.llm = llm
        self.inventory_manager = inventory_manager
        self.name = 'Procurement Agent'
        self.prompt = ChatPromptTemplate.from_template(
            """
You are a Procurement Agent responsible for checking material availability and calculating costs.

Current Inventory Data:
{inventory}

Product BOM Data:
{materials}

Task: Analyze the following order request and provide:
1. Whether all materials are available
2. Total material cost
3. Any concerns or notes
4. Your confidence level (0.0-1.0)

Order Request:
- Product SKU: {product_sku}
- Quantity: {quantity}

Provide your analysis in JSON format with keys: can_proceed, reasoning, material_availability, total_cost, confidence
"""
        )

    def invoke(self, order: dict, inventory: List[dict], materials: List[dict]) -> Dict:
        logger.info('[%s] Analyzing availability for %s x%s', self.name, order['product_sku'], order['quantity'])

        deterministic = self._deterministic_inventory_check(order)
        prompt_value = self.prompt.format(
            inventory=json.dumps(inventory, indent=2),
            materials=json.dumps(materials, indent=2),
            product_sku=order['product_sku'],
            quantity=order['quantity'],
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            response_text = response.content
            logger.info('[%s] Analysis: %s...', self.name, response_text[:200])

            analysis = self._extract_json_or_parse(response_text, deterministic)
            llm_reasoning = analysis.get('reasoning', response_text)
            final_reasoning = (
                deterministic.get('reasoning', llm_reasoning)
                if not deterministic['can_proceed']
                else llm_reasoning
            )
            return {
                'agent': self.name,
                # Procurement gate should be grounded in deterministic inventory math.
                'can_proceed': deterministic['can_proceed'],
                'reasoning': final_reasoning,
                'llm_reasoning': llm_reasoning,
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.7)),
                'total_cost': float(deterministic.get('total_cost', 0) or 0),
                'material_availability': deterministic.get('material_availability', {}),
                'decision_source': 'deterministic_inventory',
            }
        except Exception as exc:
            logger.error('[%s] Error: %s', self.name, str(exc))
            return {
                'agent': self.name,
                'can_proceed': deterministic['can_proceed'],
                'reasoning': f"LLM error: {str(exc)}. {deterministic.get('reasoning', '')}",
                'llm_reasoning': str(exc),
                'analysis': str(exc),
                'confidence': float(deterministic.get('confidence', 0.7)),
                'total_cost': float(deterministic.get('total_cost', 0) or 0),
                'material_availability': deterministic.get('material_availability', {}),
                'decision_source': 'deterministic_inventory',
            }

    def _extract_json_or_parse(self, response_text: str, deterministic: Dict) -> Dict:
        match = re.search(r'\{.*?\}', response_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                merged = dict(deterministic)
                merged.update(parsed)
                return merged
            except json.JSONDecodeError:
                pass
        parsed = self._parse_analysis(response_text)
        merged = dict(deterministic)
        merged.update(parsed)
        return merged

    def _parse_analysis(self, text: str) -> Dict:
        return {
            'reasoning': text,
            'confidence': 0.78,
        }

    def _deterministic_inventory_check(self, order: dict) -> Dict:
        sku = order.get('product_sku')
        quantity = int(order.get('quantity') or 0)
        bom = self.inventory_manager.get_product_bom(sku)
        if not bom:
            return {
                'can_proceed': False,
                'reasoning': f'Product SKU "{sku}" not found in material BOM.',
                'confidence': 0.95,
                'total_cost': 0.0,
                'material_availability': {},
            }

        material_availability = {}
        total_cost = 0.0
        can_proceed = True

        for material_id, qty_per_unit in bom.get('materials', {}).items():
            required = qty_per_unit * quantity
            available = int(self.inventory_manager.get_material_stock(material_id) or 0)
            unit_cost = float(self.inventory_manager.get_material_price(material_id) or 0.0)
            is_available = available >= required
            if not is_available:
                can_proceed = False

            line_cost = required * unit_cost
            total_cost += line_cost
            material_availability[material_id] = {
                'required': required,
                'available': available,
                'is_available': is_available,
                'unit_cost': unit_cost,
                'line_cost': round(line_cost, 2),
            }

        if can_proceed:
            reasoning = 'All required materials are available in inventory.'
            confidence = 0.93
        else:
            shortages = [mid for mid, info in material_availability.items() if not info['is_available']]
            reasoning = f"Insufficient inventory for: {', '.join(shortages)}."
            confidence = 0.9

        return {
            'can_proceed': can_proceed,
            'reasoning': reasoning,
            'confidence': confidence,
            'total_cost': round(total_cost, 2),
            'material_availability': material_availability,
        }
