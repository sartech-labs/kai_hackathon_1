import speech_recognition as sr

r = sr.Recognizer()

print("Available microphones:")
print(sr.Microphone.list_microphone_names())

with sr.Microphone() as source:
    print("🎤 Speak something...")
    r.adjust_for_ambient_noise(source)
    audio = r.listen(source)

print("📡 Audio captured")

try:
    text = r.recognize_google(audio)
    print("🗣 Recognized text:", text)
except sr.UnknownValueError:
    print("❌ Could not understand audio")
except sr.RequestError as e:
    print("❌ Recognition service error:", e)