"""
Configuration file for the Multi-Agent Order Processing System
"""

# Agent Configuration
PROCUREMENT_AGENT = {
    'name': 'Procurement Agent',
    'confidence_threshold': 0.75,
    'enabled': True
}

LOGISTICS_AGENT = {
    'name': 'Logistics Agent',
    'confidence_threshold': 0.75,
    'enabled': True,
    'base_shipping_cost_per_km': 0.5,
    'distance_mapping': {
        'local': 50,
        'regional': 300,
        'national': 1000,
        'international': 5000
    },
    'lead_time_days': {
        'local': 2,
        'regional': 5,
        'national': 7,
        'international': 14
    }
}

CONSOLIDATION_AGENT = {
    'name': 'Consolidation Agent',
    'confidence_threshold': 0.75,
    'enabled': True,
    'profit_margin': 0.25,  # 25%
    'discount_tiers': {
        'small': {'min': 0, 'max': 10, 'discount': 0.0},
        'medium': {'min': 11, 'max': 50, 'discount': 0.05},
        'large': {'min': 51, 'max': 100, 'discount': 0.10},
        'bulk': {'min': 101, 'max': float('inf'), 'discount': 0.15}
    }
}

MANAGER_AGENT = {
    'name': 'Manager Agent',
    'consensus_confidence_threshold': 0.75,  # Average confidence across all agents
    'enabled': True
}

# API Configuration
API_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True
}

# Data Files
DATA_FILES = {
    'inventory': 'data/inventory.json',
    'materials': 'data/materials.json'
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# Feature Flags
FEATURES = {
    'enable_multi_supplier': False,
    'enable_price_negotiation': False,
    'enable_webhook_notifications': False,
    'enable_agent_debate_logging': True,
    'enable_real_time_tracking': False
}
