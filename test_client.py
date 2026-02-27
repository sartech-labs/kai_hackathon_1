"""
Test Client for the Multi-Agent Order Processing System API
Run this script to test the API endpoints without using cURL
"""

import requests
import json
from datetime import datetime

# API Base URL
API_URL = "http://localhost:5000"

class APITestClient:
    """Simple client for testing API endpoints"""
    
    def __init__(self, base_url=API_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self):
        """Check if API is running"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
    
    def process_order(self, order_id, product_sku, quantity, customer_location, priority="normal"):
        """Send an order to the API"""
        payload = {
            "order_id": order_id,
            "product_sku": product_sku,
            "quantity": quantity,
            "customer_location": customer_location,
            "priority": priority
        }
        
        response = self.session.post(
            f"{self.base_url}/process_order",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        return response.status_code, response.json()
    
    def get_products(self):
        """Get list of available products"""
        response = self.session.get(f"{self.base_url}/products")
        return response.status_code, response.json()
    
    def get_inventory(self):
        """Get current inventory"""
        response = self.session.get(f"{self.base_url}/inventory")
        return response.status_code, response.json()
    
    def get_product_details(self, sku):
        """Get details for a specific product"""
        response = self.session.get(f"{self.base_url}/product/{sku}")
        return response.status_code, response.json()


def print_response(title, status_code, data):
    """Pretty print API response"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}")
    print(f"Status Code: {status_code}")
    print(f"\nResponse:")
    print(json.dumps(data, indent=2))
    print(f"{'='*70}\n")


def main():
    """Run test suite"""
    
    print("\n" + "="*70)
    print("Multi-Agent Order Processing System - API Test Client")
    print("="*70)
    
    client = APITestClient()
    
    # Check if API is running
    print("\n[1/7] Checking API health...")
    if not client.health_check():
        print("❌ ERROR: API is not running!")
        print("Please start the API server by running: python api.py")
        return
    print("✅ API is running and healthy!")
    
    # Test 1: Get Products
    print("\n[2/7] Fetching available products...")
    status, data = client.get_products()
    print_response("Available Products", status, data)
    
    # Test 2: Get Inventory
    print("\n[3/7] Fetching inventory...")
    status, data = client.get_inventory()
    print_response("Inventory Status", status, data)
    if status == 200 and data.get('status') == 'SUCCESS':
        print(f"Total materials in inventory: {len(data.get('inventory', []))}")
    
    # Test 3: Get Product Details
    print("\n[4/7] Fetching product details for PMP-STD-100...")
    status, data = client.get_product_details("PMP-STD-100")
    print_response("Product Details (PMP-STD-100)", status, data)
    
    # Test 4: Process Successful Order
    print("\n[5/7] Processing successful order (small quantity, local)...")
    status, data = client.process_order(
        order_id="TEST-001",
        product_sku="PMP-STD-100",
        quantity=15,
        customer_location="local city",
        priority="normal"
    )
    print_response("Order Processing (Successful Case)", status, data)
    
    if status == 200 and data.get('status') == 'SUCCESS':
        print("✅ Order successfully processed!")
        print(f"   Final Price: ${data.get('final_price', 'N/A')}")
        print(f"   Delivery Date: {data.get('delivery_date', 'N/A')}")
        print(f"   Consensus: {data.get('consensus_reached', False)}")
    
    # Test 5: Process Large Order
    print("\n[6/7] Processing large order (bulk quantity, expedited)...")
    status, data = client.process_order(
        order_id="TEST-002",
        product_sku="PMP-HEAVY-200",
        quantity=50,
        customer_location="national",
        priority="expedited"
    )
    print_response("Order Processing (Large Quantity with Expedited Shipping)", status, data)
    
    if status == 200 and data.get('status') == 'SUCCESS':
        print("✅ Large order successfully processed!")
        print(f"   Final Price: ${data.get('final_price', 'N/A')}")
        print(f"   Discount Applied: {data.get('cost_breakdown', {}).get('discount_rate', 0) * 100:.1f}%")
        print(f"   Delivery Date: {data.get('delivery_date', 'N/A')}")
    
    # Test 6: Process Failed Order (Insufficient Stock)
    print("\n[7/7] Processing order with insufficient stock (should fail)...")
    status, data = client.process_order(
        order_id="TEST-003",
        product_sku="PMP-CHEM-300",
        quantity=500,  # High quantity to trigger stock shortage
        customer_location="international",
        priority="normal"
    )
    print_response("Order Processing (Insufficient Stock - Expected to Fail)", status, data)
    
    if status != 200 or data.get('status') == 'FAILURE':
        print("✅ Order correctly rejected due to stock limitations!")
        print(f"   Reason: {data.get('message', 'N/A')}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUITE COMPLETED")
    print("="*70)
    print("""
Key Observations:
✓ Agent 1 (Procurement): Checks availability and calculates costs
✓ Agent 2 (Logistics): Determines shipping and delivery timeline
✓ Agent 3 (Consolidation): Calculates final pricing with discounts
✓ Manager Agent: Ensures consensus before confirming orders

Test Results:
- Small orders should succeed with no discount
- Medium orders (11-50 units) should get 5% discount
- Large orders (51-100 units) should get 10% discount
- Bulk orders (100+ units) should get 15% discount
- Orders exceeding inventory should fail with consensus rejection

To explore further:
1. Change order quantities to see different discount tiers
2. Change customer locations to see different shipping costs
3. Try invalid product SKUs to see error handling
4. Monitor the console output from 'python api.py' to see detailed logs
    """)


if __name__ == "__main__":
    main()
