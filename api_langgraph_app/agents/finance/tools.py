TOOLS = [
    {
        'name': 'compute_unit_economics',
        'description': 'Run margin analysis at a given price point',
        'parameters': {'price': 'number', 'overtime_hours': 'number'},
    },
    {
        'name': 'calculate_rush_surcharge',
        'description': 'Calculate rush surcharge to meet margin floor',
        'parameters': {'base_price': 'number', 'surcharge_rate': 'number'},
    },
    {
        'name': 'negotiate_price',
        'description': 'Open price negotiation with initial position',
        'parameters': {'initial_price': 'number'},
    },
    {
        'name': 'compute_compromise',
        'description': 'Test a compromise price point against margin thresholds',
        'parameters': {'offer_price': 'number'},
    },
    {
        'name': 'verify_final_margin',
        'description': 'Final margin verification at locked price',
        'parameters': {'final_price': 'number'},
    },
]
