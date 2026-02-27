# intake_agent/schema.py

REQUIRED_FIELDS = {
    "product_sku": None,
    "quantity": None,
    "requested_delivery_days": None,
    "offered_price_per_unit": None
}

QUESTION_MAP = {
    "product_sku": "Which product are you ordering? Please provide the SKU.",
    "quantity": "How many units do you need?",
    "requested_delivery_days": "In how many days do you need delivery?",
    "offered_price_per_unit": "What price per unit are you offering?"
}