import pyttsx3

engine = pyttsx3.init()

engine.setProperty('rate', 170)
engine.setProperty('volume', 1.0)  # Max volume

voices = engine.getProperty('voices')
print("Available voices:", voices)

engine.say("Testing speaker output.")
engine.runAndWait()