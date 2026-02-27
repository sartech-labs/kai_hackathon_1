"""
Flask API endpoint for the Multi-Agent Order Processing System
This module provides REST API endpoints for processing orders through the multi-agent system
"""

from flask import Flask, request, jsonify
from main import (
    OrderRequest, InventoryManager, ManagerAgent
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize the multi-agent system
inventory_manager = InventoryManager('data/inventory.json', 'data/materials.json')
manager = ManagerAgent(inventory_manager)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Multi-Agent Order Processing System'
    })


@app.route('/process_order', methods=['POST'])
def process_order():
    """
    Main endpoint to process orders through the multi-agent system
    
    Expected JSON body:
    {
        "order_id": "ORD-001",
        "product_sku": "PMP-STD-100",
        "quantity": 15,
        "customer_location": "local city",
        "priority": "normal"  # Optional: "normal" or "expedited"
    }
    
    Returns:
    {
        "status": "SUCCESS" | "FAILURE",
        "order_id": "ORD-001",
        "final_price": <float>,
        "total_deal_value": <float>,
        "delivery_date": "YYYY-MM-DD",
        "cost_breakdown": {...},
        "consensus_reached": <bool>,
        "timestamp": "ISO-8601 timestamp"
    }
    """
    try:
        # Validate request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'FAILURE',
                'message': 'Request body is empty'
            }), 400
        
        # Validate required fields
        required_fields = ['order_id', 'product_sku', 'quantity', 'customer_location']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'status': 'FAILURE',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create order request
        order_request = OrderRequest(
            order_id=data['order_id'],
            product_sku=data['product_sku'],
            quantity=int(data['quantity']),
            customer_location=data['customer_location'],
            priority=data.get('priority', 'normal')
        )
        
        # Validate order request
        if order_request.quantity <= 0:
            return jsonify({
                'status': 'FAILURE',
                'message': 'Quantity must be greater than 0'
            }), 400
        
        # Process order through multi-agent system
        response = manager.process_order(order_request)
        
        # Return response with appropriate status code
        status_code = 200 if response['status'] == 'SUCCESS' else 400
        return jsonify(response), status_code
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'status': 'FAILURE',
            'message': f'Validation error: {str(e)}'
        }), 400
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'status': 'FAILURE',
            'message': f'Internal server error: {str(e)}'
        }), 500


@app.route('/products', methods=['GET'])
def get_available_products():
    """Get list of available products"""
    try:
        products = inventory_manager.materials
        return jsonify({
            'status': 'SUCCESS',
            'products': products
        })
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return jsonify({
            'status': 'FAILURE',
            'message': str(e)
        }), 500


@app.route('/inventory', methods=['GET'])
def get_inventory():
    """Get current inventory status"""
    try:
        inventory = inventory_manager.inventory
        return jsonify({
            'status': 'SUCCESS',
            'inventory': inventory
        })
    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        return jsonify({
            'status': 'FAILURE',
            'message': str(e)
        }), 500


@app.route('/product/<sku>', methods=['GET'])
def get_product_details(sku):
    """Get detailed information about a specific product"""
    try:
        bom = inventory_manager.get_product_bom(sku)
        
        if not bom:
            return jsonify({
                'status': 'FAILURE',
                'message': f'Product SKU "{sku}" not found'
            }), 404
        
        # Enhance with pricing information
        materials_info = []
        total_material_cost = 0
        
        for material_id, qty_per_unit in bom['materials'].items():
            unit_cost = inventory_manager.get_material_price(material_id)
            available_stock = inventory_manager.get_material_stock(material_id)
            
            material_info = {
                'material_id': material_id,
                'quantity_per_unit': qty_per_unit,
                'unit_cost': unit_cost,
                'line_cost': (unit_cost or 0) * qty_per_unit,
                'available_stock': available_stock
            }
            materials_info.append(material_info)
            total_material_cost += material_info['line_cost']
        
        return jsonify({
            'status': 'SUCCESS',
            'product': {
                'sku': sku,
                'materials': materials_info,
                'total_material_cost_per_unit': round(total_material_cost, 2)
            }
        })
    
    except Exception as e:
        logger.error(f"Error fetching product details: {str(e)}")
        return jsonify({
            'status': 'FAILURE',
            'message': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'status': 'FAILURE',
        'message': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'status': 'FAILURE',
        'message': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Run Flask app
    # In production, use a WSGI server like Gunicorn or uWSGI
    app.run(debug=True, host='0.0.0.0', port=5000)
