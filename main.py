import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

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


@dataclass
class AgentResponse:
    """Response structure from each agent"""
    agent_name: str
    can_proceed: bool
    reasoning: str
    details: Dict
    confidence: float


class InventoryManager:
    """Manages inventory and material availability"""
    
    def __init__(self, inventory_file: str, materials_file: str):
        self.inventory = self._load_json(inventory_file)
        self.materials = self._load_json(materials_file)
    
    def _load_json(self, filepath: str) -> List:
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_inventory_dict(self) -> Dict:
        """Convert inventory list to dictionary for easy lookup"""
        return {item['material_id']: item for item in self.inventory}
    
    def get_materials_dict(self) -> Dict:
        """Convert materials list to dictionary for easy lookup"""
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


class ProcurementAgent:
    """Agent 1: Checks material availability and pricing"""
    
    def __init__(self, inventory_manager: InventoryManager):
        self.inventory_manager = inventory_manager
        self.name = "Procurement Agent"
    
    def evaluate(self, product_sku: str, quantity: int) -> AgentResponse:
        """Check if materials are available for the product"""
        logger.info(f"[{self.name}] Evaluating availability for {product_sku} x{quantity}")
        
        bom = self.inventory_manager.get_product_bom(product_sku)
        
        if not bom:
            return AgentResponse(
                agent_name=self.name,
                can_proceed=False,
                reasoning=f"Product SKU '{product_sku}' not found in materials database",
                details={},
                confidence=1.0
            )
        
        total_unit_cost = 0
        availability_check = {}
        all_available = True
        
        # Check each material required for the BOM
        for material_id, qty_per_unit in bom['materials'].items():
            required_qty = qty_per_unit * quantity
            available_stock = self.inventory_manager.get_material_stock(material_id)
            unit_cost = self.inventory_manager.get_material_price(material_id)
            
            is_available = available_stock and available_stock >= required_qty
            availability_check[material_id] = {
                'required': required_qty,
                'available': available_stock or 0,
                'is_available': is_available,
                'unit_cost': unit_cost
            }
            
            if not is_available:
                all_available = False
            
            total_unit_cost += (unit_cost or 0) * qty_per_unit
        
        response = AgentResponse(
            agent_name=self.name,
            can_proceed=all_available,
            reasoning="All materials are in stock" if all_available else "Some materials are out of stock",
            details={
                'product_sku': product_sku,
                'quantity': quantity,
                'material_availability': availability_check,
                'total_unit_cost': round(total_unit_cost, 2),
                'total_cost': round(total_unit_cost * quantity, 2)
            },
            confidence=0.95 if all_available else 0.7
        )
        
        return response


class LogisticsAgent:
    """Agent 2: Handles logistics and freight booking"""
    
    def __init__(self):
        self.name = "Logistics Agent"
        self.base_shipping_cost_per_km = 0.5
        self.distance_mapping = {
            'local': 50,
            'regional': 300,
            'national': 1000,
            'international': 5000
        }
        self.lead_time_days = {
            'local': 2,
            'regional': 5,
            'national': 7,
            'international': 14
        }
    
    def evaluate(self, customer_location: str, total_cost: float, quantity: int, priority: str = "normal") -> AgentResponse:
        """Calculate shipping costs and delivery dates"""
        logger.info(f"[{self.name}] Calculating logistics for {customer_location}")
        
        # Determine location type (simplified)
        location_type = self._determine_location_type(customer_location)
        distance = self.distance_mapping.get(location_type, 500)
        
        # Calculate shipping cost
        base_shipping = distance * self.base_shipping_cost_per_km
        weight_factor = quantity * 0.5  # Assume each unit weighs 0.5 units
        shipping_cost = base_shipping + (weight_factor * 2)
        
        # Calculate delivery date
        lead_days = self.lead_time_days.get(location_type, 7)
        if priority == "expedited":
            lead_days = max(1, lead_days // 2)
        
        delivery_date = (datetime.now() + timedelta(days=lead_days)).strftime("%Y-%m-%d")
        
        response = AgentResponse(
            agent_name=self.name,
            can_proceed=True,
            reasoning=f"Shipping to {location_type} location - {distance}km distance",
            details={
                'location_type': location_type,
                'distance_km': distance,
                'shipping_cost': round(shipping_cost, 2),
                'delivery_date': delivery_date,
                'lead_time_days': lead_days,
                'priority': priority
            },
            confidence=0.9
        )
        
        return response
    
    def _determine_location_type(self, location: str) -> str:
        """Simplified location type determination"""
        location_lower = location.lower()
        
        if any(word in location_lower for word in ['same', 'city', 'local']):
            return 'local'
        elif any(word in location_lower for word in ['state', 'region']):
            return 'regional'
        elif any(word in location_lower for word in ['country', 'domestic', 'national']):
            return 'national'
        else:
            return 'international'


class ConsolidationAgent:
    """Agent 3: Consolidates responses and calculates final deal value"""
    
    def __init__(self):
        self.name = "Consolidation Agent"
        self.profit_margin = 0.25  # 25% profit margin
        self.discount_tiers = {
            'small': (0, 10, 0.0),
            'medium': (11, 50, 0.05),
            'large': (51, 100, 0.10),
            'bulk': (101, float('inf'), 0.15)
        }
    
    def consolidate(self, procurement_response: AgentResponse, logistics_response: AgentResponse, quantity: int) -> AgentResponse:
        """Consolidate responses from other agents and calculate final deal"""
        logger.info(f"[{self.name}] Consolidating deal structure")
        
        if not procurement_response.can_proceed or not logistics_response.can_proceed:
            return AgentResponse(
                agent_name=self.name,
                can_proceed=False,
                reasoning="Cannot proceed due to procurement or logistics constraints",
                details={},
                confidence=0.0
            )
        
        # Extract data from other agents
        material_cost = procurement_response.details.get('total_cost', 0)
        shipping_cost = logistics_response.details.get('shipping_cost', 0)
        delivery_date = logistics_response.details.get('delivery_date', '')
        
        # Calculate discount based on quantity
        discount_rate = self._get_discount_rate(quantity)
        
        # Calculate final pricing
        subtotal = material_cost + shipping_cost
        discount_amount = subtotal * discount_rate
        discounted_subtotal = subtotal - discount_amount
        
        # Apply profit margin
        final_price = discounted_subtotal * (1 + self.profit_margin)
        total_deal_value = final_price  # The total value including profit
        
        response = AgentResponse(
            agent_name=self.name,
            can_proceed=True,
            reasoning=f"Deal consolidated with {discount_rate*100:.0f}% volume discount",
            details={
                'material_cost': round(material_cost, 2),
                'shipping_cost': round(shipping_cost, 2),
                'subtotal': round(subtotal, 2),
                'discount_rate': discount_rate,
                'discount_amount': round(discount_amount, 2),
                'discounted_subtotal': round(discounted_subtotal, 2),
                'profit_margin': self.profit_margin,
                'final_price': round(final_price, 2),
                'total_deal_value': round(total_deal_value, 2),
                'delivery_date': delivery_date,
                'quantity': quantity
            },
            confidence=0.95
        )
        
        return response
    
    def _get_discount_rate(self, quantity: int) -> float:
        """Determine discount rate based on quantity tier"""
        for tier_name, (min_qty, max_qty, rate) in self.discount_tiers.items():
            if min_qty <= quantity <= max_qty:
                return rate
        return 0.0


class ManagerAgent:
    """Manager Agent: Orchestrates all other agents and manages consensus"""
    
    def __init__(self, inventory_manager: InventoryManager):
        self.name = "Manager Agent"
        self.procurement_agent = ProcurementAgent(inventory_manager)
        self.logistics_agent = LogisticsAgent()
        self.consolidation_agent = ConsolidationAgent()
        self.agents = [self.procurement_agent, self.logistics_agent, self.consolidation_agent]
    
    def process_order(self, request: OrderRequest) -> Dict:
        """Process an order through the multi-agent system"""
        logger.info(f"\n{'='*60}")
        logger.info(f"[{self.name}] Processing Order: {request.order_id}")
        logger.info(f"[{self.name}] Request: {request.product_sku} x{request.quantity} to {request.customer_location}")
        logger.info(f"{'='*60}\n")
        
        # Step 1: Procurement Agent evaluates availability
        logger.info("[STEP 1] Procurement Agent Evaluation")
        procurement_response = self.procurement_agent.evaluate(
            request.product_sku,
            request.quantity
        )
        logger.info(f"  Result: {procurement_response.reasoning}")
        logger.info(f"  Confidence: {procurement_response.confidence*100:.0f}%\n")
        
        # Step 2: Logistics Agent evaluates shipping
        logger.info("[STEP 2] Logistics Agent Evaluation")
        logistics_response = self.logistics_agent.evaluate(
            request.customer_location,
            procurement_response.details.get('total_cost', 0),
            request.quantity,
            request.priority
        )
        logger.info(f"  Result: {logistics_response.reasoning}")
        logger.info(f"  Delivery Date: {logistics_response.details.get('delivery_date')}")
        logger.info(f"  Confidence: {logistics_response.confidence*100:.0f}%\n")
        
        # Step 3: Consolidation Agent calculates final deal
        logger.info("[STEP 3] Consolidation Agent Evaluation")
        consolidation_response = self.consolidation_agent.consolidate(
            procurement_response,
            logistics_response,
            request.quantity
        )
        logger.info(f"  Result: {consolidation_response.reasoning}")
        logger.info(f"  Confidence: {consolidation_response.confidence*100:.0f}%\n")
        
        # Step 4: Check consensus
        logger.info("[STEP 4] Consensus Check")
        consensus_reached = self._check_consensus(
            [procurement_response, logistics_response, consolidation_response]
        )
        logger.info(f"  Consensus Reached: {consensus_reached}\n")
        
        # Generate final response
        final_response = self._generate_final_response(
            request,
            consolidation_response,
            consensus_reached
        )
        
        return final_response
    
    def _check_consensus(self, agent_responses: List[AgentResponse]) -> bool:
        """Check if agents have reached consensus"""
        # Consensus requires:
        # 1. All agents can proceed
        # 2. Average confidence > 0.75
        
        all_can_proceed = all(response.can_proceed for response in agent_responses)
        avg_confidence = sum(response.confidence for response in agent_responses) / len(agent_responses)
        
        consensus = all_can_proceed and avg_confidence > 0.75
        
        logger.info(f"  All Agents Can Proceed: {all_can_proceed}")
        logger.info(f"  Average Confidence: {avg_confidence*100:.0f}%")
        
        return consensus
    
    def _generate_final_response(self, request: OrderRequest, consolidation_response: AgentResponse, consensus: bool) -> Dict:
        """Generate the final API response"""
        if not consolidation_response.can_proceed or not consensus:
            return {
                'status': 'FAILURE',
                'order_id': request.order_id,
                'message': 'Order cannot be processed. Consensus not reached.',
                'timestamp': datetime.now().isoformat()
            }
        
        details = consolidation_response.details
        
        response = {
            'status': 'SUCCESS',
            'order_id': request.order_id,
            'product_sku': request.product_sku,
            'quantity': request.quantity,
            'customer_location': request.customer_location,
            'final_price': details.get('final_price'),
            'total_deal_value': details.get('total_deal_value'),
            'delivery_date': details.get('delivery_date'),
            'cost_breakdown': {
                'material_cost': details.get('material_cost'),
                'shipping_cost': details.get('shipping_cost'),
                'discount_amount': details.get('discount_amount'),
                'discount_rate': details.get('discount_rate'),
                'profit_margin': details.get('profit_margin')
            },
            'consensus_reached': consensus,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"\n{'='*60}")
        logger.info("FINAL RESPONSE:")
        logger.info(f"{'='*60}")
        logger.info(json.dumps(response, indent=2))
        logger.info(f"{'='*60}\n")
        
        return response


def main():
    """Main entry point for testing the multi-agent system"""
    
    # Initialize the system
    inventory_manager = InventoryManager(
        'data/inventory.json',
        'data/materials.json'
    )
    
    manager = ManagerAgent(inventory_manager)
    
    # Test Case 1: Standard order
    print("\n" + "="*80)
    print("TEST CASE 1: Standard Order - Local Delivery")
    print("="*80)
    request1 = OrderRequest(
        order_id="ORD-001",
        product_sku="PMP-STD-100",
        quantity=15,
        customer_location="local city",
        priority="normal"
    )
    response1 = manager.process_order(request1)
    
    # Test Case 2: Large order with expedited shipping
    print("\n" + "="*80)
    print("TEST CASE 2: Large Order - National Delivery with Expedited Shipping")
    print("="*80)
    request2 = OrderRequest(
        order_id="ORD-002",
        product_sku="PMP-HEAVY-200",
        quantity=50,
        customer_location="national",
        priority="expedited"
    )
    response2 = manager.process_order(request2)
    
    # Test Case 3: Bulk order with maximum discount
    print("\n" + "="*80)
    print("TEST CASE 3: Bulk Order - Regional Delivery")
    print("="*80)
    request3 = OrderRequest(
        order_id="ORD-003",
        product_sku="PMP-CHEM-300",
        quantity=120,
        customer_location="regional state",
        priority="normal"
    )
    response3 = manager.process_order(request3)
    
    # Test Case 4: Insufficient inventory
    print("\n" + "="*80)
    print("TEST CASE 4: Order Exceeding Available Stock (Should Fail)")
    print("="*80)
    request4 = OrderRequest(
        order_id="ORD-004",
        product_sku="PMP-CHEM-300",
        quantity=500,
        customer_location="international",
        priority="normal"
    )
    response4 = manager.process_order(request4)
    
    # Test Case 5: Invalid product
    print("\n" + "="*80)
    print("TEST CASE 5: Invalid Product SKU (Should Fail)")
    print("="*80)
    request5 = OrderRequest(
        order_id="ORD-005",
        product_sku="PMP-INVALID",
        quantity=10,
        customer_location="local city",
        priority="normal"
    )
    response5 = manager.process_order(request5)


if __name__ == "__main__":
    main()
