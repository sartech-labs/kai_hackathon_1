"""
LangGraph-based Multi-Agent Order Processing System
Uses LLM (OpenAI) for intelligent agent decision-making
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import LangChain and LangGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
# from langgraph.graph import CompiledGraph
from typing import TypedDict, Annotated
import operator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    """Represents an incoming order request"""
    order_id: str
    product_sku: str
    quantity: int
    customer_location: str
    priority: str = "normal"


class LLMAgentState(TypedDict):
    """State for LLM-based agents in LangGraph"""
    order: dict
    inventory: list
    materials: list
    procurement_analysis: Optional[str]
    logistics_analysis: Optional[str]
    consolidation_analysis: Optional[str]
    messages: Annotated[List[BaseMessage], operator.add]
    all_can_proceed: bool
    final_decision: Optional[str]


class InventoryManager:
    """Manages inventory and material availability"""
    
    def __init__(self, inventory_file: str, materials_file: str):
        self.inventory = self._load_json(inventory_file)
        self.materials = self._load_json(materials_file)
    
    def _load_json(self, filepath: str) -> List:
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_inventory_dict(self) -> Dict:
        """Convert inventory list to dictionary"""
        return {item['material_id']: item for item in self.inventory}
    
    def get_materials_dict(self) -> Dict:
        """Convert materials list to dictionary"""
        return {item['sku']: item for item in self.materials}
    
    def get_product_bom(self, sku: str) -> Optional[Dict]:
        """Get Bill of Materials for a product"""
        for material in self.materials:
            if material['sku'] == sku:
                return material
        return None
    
    def get_material_price(self, material_id: str) -> Optional[float]:
        """Get unit cost of a material"""
        for item in self.inventory:
            if item['material_id'] == material_id:
                return item['unit_cost']
        return None
    
    def get_material_stock(self, material_id: str) -> Optional[int]:
        """Get available stock of a material"""
        for item in self.inventory:
            if item['material_id'] == material_id:
                return item['stock']
        return None


class LLMProcurementAgent:
    """Agent 1: LLM-based Procurement Agent"""
    
    def __init__(self, llm: ChatOpenAI, inventory_manager: InventoryManager):
        self.llm = llm
        self.inventory_manager = inventory_manager
        self.name = "Procurement Agent"
        
        self.prompt = ChatPromptTemplate.from_template("""
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
""")
    
    def invoke(self, order: dict, inventory: list, materials: list) -> Dict:
        """Analyze procurement for the order"""
        logger.info(f"[{self.name}] Analyzing availability for {order['product_sku']} x{order['quantity']}")
        
        inventory_str = json.dumps(inventory, indent=2)
        materials_str = json.dumps(materials, indent=2)
        
        prompt_value = self.prompt.format(
            inventory=inventory_str,
            materials=materials_str,
            product_sku=order['product_sku'],
            quantity=order['quantity']
        )
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            
            # Parse the response
            response_text = response.content
            logger.info(f"[{self.name}] Analysis: {response_text[:200]}...")
            
            # Try to extract JSON from response
            try:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = self._parse_analysis(response_text)
            except:
                analysis = self._parse_analysis(response_text)
            
            return {
                'agent': self.name,
                'can_proceed': analysis.get('can_proceed', False),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.7))
            }
        except Exception as e:
            logger.error(f"[{self.name}] Error: {str(e)}")
            return {
                'agent': self.name,
                'can_proceed': False,
                'reasoning': f"Error in analysis: {str(e)}",
                'analysis': str(e),
                'confidence': 0.0
            }
    
    def _parse_analysis(self, text: str) -> Dict:
        """Parse analysis from LLM response"""
        return {
            'can_proceed': 'available' in text.lower() or 'proceed' in text.lower(),
            'reasoning': text,
            'confidence': 0.85 if 'available' in text.lower() else 0.5
        }


class LLMLogisticsAgent:
    """Agent 2: LLM-based Logistics Agent"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Logistics Agent"
        
        self.prompt = ChatPromptTemplate.from_template("""
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

Provide your analysis in JSON format with keys: location_type, shipping_cost, delivery_date, reasoning, confidence
""")
    
    def invoke(self, order: dict, material_cost: float) -> Dict:
        """Analyze logistics for the order"""
        logger.info(f"[{self.name}] Calculating logistics for {order['customer_location']}")
        
        prompt_value = self.prompt.format(
            product_sku=order['product_sku'],
            quantity=order['quantity'],
            customer_location=order['customer_location'],
            priority=order.get('priority', 'normal'),
            material_cost=material_cost
        )
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            
            response_text = response.content
            logger.info(f"[{self.name}] Analysis: {response_text[:200]}...")
            
            try:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = self._parse_analysis(response_text)
            except:
                analysis = self._parse_analysis(response_text)
            
            return {
                'agent': self.name,
                'can_proceed': True,
                'location_type': analysis.get('location_type', 'unknown'),
                'shipping_cost': float(analysis.get('shipping_cost', 50)),
                'delivery_date': analysis.get('delivery_date', self._default_delivery_date(order.get('priority'))),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.8))
            }
        except Exception as e:
            logger.error(f"[{self.name}] Error: {str(e)}")
            return {
                'agent': self.name,
                'can_proceed': True,
                'location_type': 'unknown',
                'shipping_cost': 50.0,
                'delivery_date': self._default_delivery_date(order.get('priority')),
                'reasoning': f"Error in analysis: {str(e)}",
                'analysis': str(e),
                'confidence': 0.5
            }
    
    def _parse_analysis(self, text: str) -> Dict:
        """Parse analysis from LLM response"""
        return {
            'location_type': 'regional' if 'region' in text.lower() else 'local',
            'shipping_cost': 50.0,
            'delivery_date': (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
            'reasoning': text,
            'confidence': 0.8
        }
    
    def _default_delivery_date(self, priority: str = "normal") -> str:
        """Get default delivery date"""
        days = 2 if priority == "expedited" else 5
        return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


class LLMConsolidationAgent:
    """Agent 3: LLM-based Consolidation Agent"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Consolidation Agent"
        
        self.prompt = ChatPromptTemplate.from_template("""
You are a Consolidation Agent responsible for finalizing pricing and deal structure.

Task: Review the procurement and logistics data, then provide:
1. Whether the deal should proceed
2. Applicable discount (based on quantity)
3. Final price calculation
4. Total deal value
5. Any recommendations
6. Your confidence level (0.0-1.0)

Procurement Analysis:
- Can Proceed: {procurement_can_proceed}
- Material Cost: {material_cost}
- Reasoning: {procurement_reasoning}

Logistics Analysis:
- Can Proceed: {logistics_can_proceed}
- Shipping Cost: {shipping_cost}
- Delivery Date: {delivery_date}
- Reasoning: {logistics_reasoning}

Order Details:
- Quantity: {quantity}
- Product: {product_sku}

Profit Margin: 25%
Discount Tiers:
- 1-10 units: 0%
- 11-50 units: 5%
- 51-100 units: 10%
- 100+ units: 15%

Provide your analysis in JSON format with keys: can_proceed, discount_rate, final_price, total_deal_value, reasoning, confidence
""")
    
    def invoke(self, procurement_result: Dict, logistics_result: Dict, order: dict) -> Dict:
        """Consolidate and finalize the deal"""
        logger.info(f"[{self.name}] Consolidating deal structure")
        
        material_cost = procurement_result.get('analysis', 'Unknown')
        
        prompt_value = self.prompt.format(
            procurement_can_proceed=procurement_result['can_proceed'],
            material_cost=material_cost,
            procurement_reasoning=procurement_result.get('reasoning', 'N/A'),
            logistics_can_proceed=logistics_result['can_proceed'],
            shipping_cost=logistics_result.get('shipping_cost', 0),
            delivery_date=logistics_result.get('delivery_date', 'N/A'),
            logistics_reasoning=logistics_result.get('reasoning', 'N/A'),
            quantity=order['quantity'],
            product_sku=order['product_sku']
        )
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt_value)])
            
            response_text = response.content
            logger.info(f"[{self.name}] Analysis: {response_text[:200]}...")
            
            try:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = self._parse_analysis(response_text, procurement_result, logistics_result, order)
            except:
                analysis = self._parse_analysis(response_text, procurement_result, logistics_result, order)
            
            return {
                'agent': self.name,
                'can_proceed': analysis.get('can_proceed', False),
                'discount_rate': float(analysis.get('discount_rate', 0)),
                'final_price': float(analysis.get('final_price', 0)),
                'total_deal_value': float(analysis.get('total_deal_value', 0)),
                'reasoning': analysis.get('reasoning', response_text),
                'analysis': response_text,
                'confidence': float(analysis.get('confidence', 0.8))
            }
        except Exception as e:
            logger.error(f"[{self.name}] Error: {str(e)}")
            return {
                'agent': self.name,
                'can_proceed': False,
                'discount_rate': 0,
                'final_price': 0,
                'total_deal_value': 0,
                'reasoning': f"Error in analysis: {str(e)}",
                'analysis': str(e),
                'confidence': 0.0
            }
    
    def _parse_analysis(self, text: str, procurement_result: Dict, logistics_result: Dict, order: dict) -> Dict:
        """Parse analysis from LLM response"""
        # Calculate default values
        discount_rate = 0.0
        if order['quantity'] >= 100:
            discount_rate = 0.15
        elif order['quantity'] >= 51:
            discount_rate = 0.10
        elif order['quantity'] >= 11:
            discount_rate = 0.05
        
        base_cost = 100000  # Default estimate
        shipping = logistics_result.get('shipping_cost', 50)
        subtotal = base_cost + shipping
        discount_amount = subtotal * discount_rate
        after_discount = subtotal - discount_amount
        final_price = after_discount * 1.25  # 25% profit margin
        
        return {
            'can_proceed': procurement_result.get('can_proceed', False) and logistics_result.get('can_proceed', False),
            'discount_rate': discount_rate,
            'final_price': final_price,
            'total_deal_value': final_price,
            'reasoning': text,
            'confidence': 0.8
        }


class LLMManagerAgent:
    """Manager Agent using LangGraph to orchestrate all agents"""
    
    def __init__(self, api_key: str, inventory_manager: InventoryManager):
        self.llm = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo", temperature=0.3)
        self.inventory_manager = inventory_manager
        self.procurement_agent = LLMProcurementAgent(self.llm, inventory_manager)
        self.logistics_agent = LLMLogisticsAgent(self.llm)
        self.consolidation_agent = LLMConsolidationAgent(self.llm)
        self.name = "Manager Agent"
        
        # Initialize LangGraph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(LLMAgentState)
        
        # Add nodes for each agent
        workflow.add_node("procurement", self._procurement_node)
        workflow.add_node("logistics", self._logistics_node)
        workflow.add_node("consolidation", self._consolidation_node)
        workflow.add_node("consensus", self._consensus_node)
        
        # Define edges
        workflow.set_entry_point("procurement")
        workflow.add_edge("procurement", "logistics")
        workflow.add_edge("logistics", "consolidation")
        workflow.add_edge("consolidation", "consensus")
        workflow.add_edge("consensus", END)
        
        return workflow.compile()
    
    def _procurement_node(self, state: LLMAgentState) -> LLMAgentState:
        """Procurement Agent node"""
        logger.info("[STEP 1] Procurement Agent Evaluation")
        
        result = self.procurement_agent.invoke(
            state['order'],
            state['inventory'],
            state['materials']
        )
        
        state['procurement_analysis'] = json.dumps(result)
        state['messages'].append(AIMessage(content=f"Procurement: {result['reasoning']}"))
        
        logger.info(f"  Result: {result['reasoning']}")
        logger.info(f"  Confidence: {result['confidence']*100:.0f}%")
        
        return state
    
    def _logistics_node(self, state: LLMAgentState) -> LLMAgentState:
        """Logistics Agent node"""
        logger.info("[STEP 2] Logistics Agent Evaluation")
        
        # Get material cost from procurement
        procurement_data = json.loads(state['procurement_analysis'])
        material_cost = 100000  # Default estimate
        
        result = self.logistics_agent.invoke(state['order'], material_cost)
        
        state['logistics_analysis'] = json.dumps(result)
        state['messages'].append(AIMessage(content=f"Logistics: {result['reasoning']}"))
        
        logger.info(f"  Result: {result['reasoning']}")
        logger.info(f"  Delivery Date: {result['delivery_date']}")
        logger.info(f"  Confidence: {result['confidence']*100:.0f}%")
        
        return state
    
    def _consolidation_node(self, state: LLMAgentState) -> LLMAgentState:
        """Consolidation Agent node"""
        logger.info("[STEP 3] Consolidation Agent Evaluation")
        
        procurement_data = json.loads(state['procurement_analysis'])
        logistics_data = json.loads(state['logistics_analysis'])
        
        result = self.consolidation_agent.invoke(
            procurement_data,
            logistics_data,
            state['order']
        )
        
        state['consolidation_analysis'] = json.dumps(result)
        state['messages'].append(AIMessage(content=f"Consolidation: {result['reasoning']}"))
        
        logger.info(f"  Result: {result['reasoning']}")
        logger.info(f"  Confidence: {result['confidence']*100:.0f}%")
        
        return state
    
    def _consensus_node(self, state: LLMAgentState) -> LLMAgentState:
        """Check consensus among all agents"""
        logger.info("[STEP 4] Consensus Check")
        
        procurement_data = json.loads(state['procurement_analysis'])
        logistics_data = json.loads(state['logistics_analysis'])
        consolidation_data = json.loads(state['consolidation_analysis'])
        
        # Check consensus
        all_can_proceed = (
            procurement_data.get('can_proceed', False) and
            logistics_data.get('can_proceed', False) and
            consolidation_data.get('can_proceed', False)
        )
        
        avg_confidence = (
            procurement_data.get('confidence', 0) +
            logistics_data.get('confidence', 0) +
            consolidation_data.get('confidence', 0)
        ) / 3
        
        consensus_reached = all_can_proceed and avg_confidence > 0.75
        
        logger.info(f"  All Agents Can Proceed: {all_can_proceed}")
        logger.info(f"  Average Confidence: {avg_confidence*100:.0f}%")
        logger.info(f"  Consensus Reached: {consensus_reached}")
        
        state['all_can_proceed'] = consensus_reached
        
        if consensus_reached:
            state['final_decision'] = "SUCCESS"
        else:
            state['final_decision'] = "FAILURE"
        
        return state
    
    def process_order(self, request: OrderRequest) -> Dict:
        """Process order through LangGraph workflow"""
        logger.info(f"\n{'='*60}")
        logger.info(f"[{self.name}] Processing Order: {request.order_id}")
        logger.info(f"[{self.name}] Request: {request.product_sku} x{request.quantity} to {request.customer_location}")
        logger.info(f"{'='*60}\n")
        
        # Prepare initial state
        initial_state: LLMAgentState = {
            'order': {
                'order_id': request.order_id,
                'product_sku': request.product_sku,
                'quantity': request.quantity,
                'customer_location': request.customer_location,
                'priority': request.priority
            },
            'inventory': self.inventory_manager.inventory,
            'materials': self.inventory_manager.materials,
            'procurement_analysis': None,
            'logistics_analysis': None,
            'consolidation_analysis': None,
            'messages': [HumanMessage(content=f"Process order: {request.order_id}")],
            'all_can_proceed': False,
            'final_decision': None
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        # Generate final response
        return self._generate_final_response(request, final_state)
    
    def _generate_final_response(self, request: OrderRequest, state: LLMAgentState) -> Dict:
        """Generate final API response"""
        consolidation_data = json.loads(state['consolidation_analysis'])
        
        if not state['all_can_proceed']:
            return {
                'status': 'FAILURE',
                'order_id': request.order_id,
                'message': 'Order cannot be processed. Consensus not reached.',
                'timestamp': datetime.now().isoformat()
            }
        
        response = {
            'status': 'SUCCESS',
            'order_id': request.order_id,
            'product_sku': request.product_sku,
            'quantity': request.quantity,
            'customer_location': request.customer_location,
            'final_price': consolidation_data.get('final_price', 0),
            'total_deal_value': consolidation_data.get('total_deal_value', 0),
            'delivery_date': json.loads(state['logistics_analysis']).get('delivery_date', ''),
            'cost_breakdown': {
                'discount_rate': consolidation_data.get('discount_rate', 0),
                'profit_margin': 0.25
            },
            'consensus_reached': state['all_can_proceed'],
            'agent_responses': {
                'procurement': json.loads(state['procurement_analysis']),
                'logistics': json.loads(state['logistics_analysis']),
                'consolidation': consolidation_data
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"\n{'='*60}")
        logger.info("FINAL RESPONSE:")
        logger.info(f"{'='*60}")
        logger.info(json.dumps(response, indent=2))
        logger.info(f"{'='*60}\n")
        
        return response


def main():
    """Main entry point for LangGraph-based system"""
    
    # Load API key
    api_key = os.getenv('OPEN_AI_API_KEY')
    if not api_key:
        logger.error("OPEN_AI_API_KEY not found in .env file")
        return
    
    # Initialize
    inventory_manager = InventoryManager(
        'data/inventory.json',
        'data/materials.json'
    )
    
    manager = LLMManagerAgent(api_key, inventory_manager)
    
    # Test Case 1
    print("\n" + "="*80)
    print("TEST CASE 1: Standard Order - LangGraph + OpenAI")
    print("="*80)
    request1 = OrderRequest(
        order_id="ORD-001",
        product_sku="PMP-STD-100",
        quantity=15,
        customer_location="local city",
        priority="normal"
    )
    response1 = manager.process_order(request1)
    
    # Test Case 2
    print("\n" + "="*80)
    print("TEST CASE 2: Large Order - LangGraph + OpenAI")
    print("="*80)
    request2 = OrderRequest(
        order_id="ORD-002",
        product_sku="PMP-HEAVY-200",
        quantity=50,
        customer_location="national",
        priority="expedited"
    )
    response2 = manager.process_order(request2)


if __name__ == "__main__":
    main()
