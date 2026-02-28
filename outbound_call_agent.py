import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv()

VAPI_API_KEY = os.environ.get('VAPI_API_KEY')
ASSISTANT_ID = os.environ.get('ASSISTANT_ID')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')

BASE_URL = "https://api.vapi.ai"

def trigger_call(customer_number):
    payload = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_NUMBER_ID,
        "customer": {
            "number": customer_number
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


@app.route("/call", methods=["POST"])
def call_endpoint():
    """
    Endpoint to trigger an outbound call.
    Expected JSON: {"customer_number": "+91xxxxxxxxxx"}
    """
    try:
        data = request.get_json()
        
        if not data or "customer_number" not in data:
            return jsonify({"error": "customer_number is required"}), 400
        
        customer_number = data.get("customer_number", "+918547476466")
        
        if not customer_number:
            return jsonify({"error": "customer_number cannot be empty"}), 400
        
        result = trigger_call(customer_number)
        return jsonify(result), 200
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
