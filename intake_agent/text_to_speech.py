import pyttsx3

engine = pyttsx3.init()

def speak(text):
    print(f"\n🤖 Agent: {text}")
    engine.say(text)
    engine.runAndWait()