TOOLS = [
    {
        'name': 'evaluate_shipping_modes',
        'description': 'Compare ground, express, and air freight for delivery window',
        'parameters': {'delivery_days': 'number'},
    },
    {
        'name': 'check_route_clearance',
        'description': 'Verify carrier availability and route clearance',
        'parameters': {'origin': 'string', 'destination': 'string', 'quantity': 'number'},
    },
    {
        'name': 're_evaluate_mode',
        'description': 'Re-check shipping mode after delivery adjustment',
        'parameters': {'delivery_days': 'number'},
    },
    {
        'name': 'book_carrier',
        'description': 'Book carrier and lock route for final delivery',
        'parameters': {'mode': 'string', 'delivery_days': 'number'},
    },
]
