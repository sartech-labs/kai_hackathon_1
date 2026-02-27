TOOLS = [
    {
        'name': 'check_production_capacity',
        'description': 'Query factory floor for available capacity and throughput',
        'parameters': {'quantity': 'number', 'delivery_days': 'number'},
    },
    {
        'name': 'calculate_overtime',
        'description': 'Compute overtime schedule and cost for production shortfall',
        'parameters': {'shortfall_days': 'number', 'max_ot_per_day': 'number'},
    },
    {
        'name': 'recalculate_schedule',
        'description': 'Re-evaluate production schedule with adjusted delivery window',
        'parameters': {'delivery_days': 'number'},
    },
    {
        'name': 'lock_production_schedule',
        'description': 'Finalize and lock the production schedule',
        'parameters': {'delivery_days': 'number', 'overtime_hours': 'number'},
    },
]
