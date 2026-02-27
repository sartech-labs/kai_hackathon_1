from intake_agent.schema import REQUIRED_FIELDS, QUESTION_MAP
from intake_agent.extractor import extract_order_info
import pyttsx3

from intake_agent.speech_to_text import record_and_transcribe

engine = pyttsx3.init()

def find_missing_fields(state):
    return [k for k, v in state.items() if v is None]


def intake_loop():
    engine.say("Welcome to SYNK Order Intake Agent")
    engine.runAndWait()
    engine.say("Please describe your order in your own words.")
    print("Please describe your order: ")
    state = REQUIRED_FIELDS.copy()

    # Initial free input
    user_input = record_and_transcribe()

    extracted = extract_order_info(user_input, state)

    for key in state:
        if key in extracted and extracted[key] is not None:
            state[key] = extracted[key]

    # Intelligent follow-up loop
    while True:
        missing = find_missing_fields(state)

        if not missing:
            print("\n✅ All required inputs collected successfully!\n")
            return state

        field = missing[0]
        question = QUESTION_MAP[field]

        engine.say(question)
        engine.runAndWait()

        user_input = record_and_transcribe()

        extracted = extract_order_info(user_input, state)

        if field in extracted and extracted[field] is not None:
            state[field] = extracted[field]
        else:
            print("⚠️ I didn't catch that clearly. Please try again.")