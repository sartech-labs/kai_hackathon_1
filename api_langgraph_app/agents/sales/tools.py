TOOLS = [
    {
        'name': 'lookup_customer_profile',
        'description': 'Retrieve customer tier, relationship history, and annual volume',
        'parameters': {'customer': 'string'},
    },
    {
        'name': 'assess_deal_sensitivity',
        'description': 'Evaluate customer sensitivity to price changes',
        'parameters': {'customer': 'string', 'proposed_price': 'number'},
    },
    {
        'name': 'calculate_counter_offer',
        'description': 'Compute counter-offer balancing margin and customer retention',
        'parameters': {'proposed_price': 'number', 'original_price': 'number'},
    },
    {
        'name': 'calculate_deal_value',
        'description': 'Compute final deal metrics for customer report',
        'parameters': {'price': 'number', 'quantity': 'number'},
    },
]
