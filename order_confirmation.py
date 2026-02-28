import requests
from dotenv import load_dotenv
import os
load_dotenv()

VAPI_API_KEY = os.environ.get('VAPI_API_KEY')
ASSISTANT_ID = os.environ.get('ASSISTANT_ID')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')

def order_confirmation_call(customer_number, order_update):
    BASE_URL = "https://api.vapi.ai"
    payload = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {
            "number": customer_number
        },
        "assistant": {
            "name": "Hardcoded Caller",
            "firstMessage": "I have an update on the order.",
            "model": {
                "provider": "openai",
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are calling to deliver a short update. "
                            "The update is: " + order_update + " "
                            "State the update clearly and then ask if they have questions. "
                            "Do not introduce yourself."
                        )
                    }
                ]
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "burt"
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{BASE_URL}/call",
        json=payload,
        headers=headers,
        timeout=10
    )

    response.raise_for_status()
    return response.json()

customer_number ="+918547476466"
order_update = "The lead for the 10 units of product A will arrive your location in kochi by 5 PM today by land."
result = order_confirmation_call(customer_number, order_update)
print(result)
