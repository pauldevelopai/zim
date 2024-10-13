from google.cloud import speech

def test_google_speech_to_text():
    client = speech.SpeechClient()
    print("Google Speech-to-Text client initialized successfully.")

if __name__ == "__main__":
    test_google_speech_to_text()