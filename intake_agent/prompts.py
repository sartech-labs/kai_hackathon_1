# intake_agent/prompts.py

def build_extraction_prompt(user_text, current_state):
    return f"""
You are an AI order intake assistant.

Extract the following fields if present:
- product_sku (string)
- quantity (integer)
- requested_delivery_days (integer)
- offered_price_per_unit (float)

Current known state:
{current_state}

User input:
"{user_text}"

Return ONLY valid JSON.
If a field is not mentioned, return null for it.
"""