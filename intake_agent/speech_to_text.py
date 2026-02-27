import speech_recognition as sr

recognizer = sr.Recognizer()

def record_and_transcribe():
    with sr.Microphone() as source:
        print("🎤 Listening... (Speak now)")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    print("📡 Audio captured successfully")  # Debug line

    try:
        text = recognizer.recognize_google(audio)
        print(f"🗣 You said (DEBUG): {text}")  # Debug confirmation
        return text
    except sr.UnknownValueError:
        print("⚠️ Could not understand audio.")
        return ""
    except sr.RequestError:
        print("⚠️ Speech recognition service unavailable.")
        return ""