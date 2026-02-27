from intake_agent.clarification_loop import intake_loop
import json

print("MAIN FILE STARTED")

def main():
    print("Calling intake loop...")
    final_order = intake_loop()

    print("\n📦 Final Structured Order JSON:\n")
    print(json.dumps(final_order, indent=4))

if __name__ == "__main__":
    main()