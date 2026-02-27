TOOLS = [
    {
        'name': 'query_supplier_inventory',
        'description': 'Check supplier for material availability and lead time',
        'parameters': {'supplier': 'string', 'quantity': 'number'},
    },
    {
        'name': 'query_alternate_supplier',
        'description': 'Check alternate supplier as backup option',
        'parameters': {'supplier': 'string', 'quantity': 'number'},
    },
    {
        'name': 'reserve_materials',
        'description': 'Reserve raw materials with selected supplier',
        'parameters': {'supplier': 'string', 'quantity': 'number'},
    },
    {
        'name': 'submit_purchase_order',
        'description': 'Submit final purchase order to supplier',
        'parameters': {'supplier': 'string', 'quantity': 'number', 'price_per_unit': 'number'},
    },
]
