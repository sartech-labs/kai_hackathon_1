# intake_agent/extractor.py

import json
import os
import re
from openai import OpenAI
from intake_agent.prompts import build_extraction_prompt

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_order_info(user_text, current_state):
    prompt = build_extraction_prompt(user_text, current_state)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    print("🔎 Raw model output:\n", content)  # DEBUG

    # Extract JSON block using regex
    match = re.search(r"\{.*\}", content, re.DOTALL)

    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            print("⚠️ JSON still malformed.")
            return {}
    else:
        print("⚠️ No JSON found in response.")
        return {}