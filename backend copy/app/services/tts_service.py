import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class TTSService:
    """Text-to-Speech service using OpenAI"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def text_to_speech_mulaw(self, text: str) -> str:
        """
        Convert text to speech - using PCM16 format
        """
        try:
            print(f"🎙️ Converting text: {text[:50]}...")

            # Generate speech as PCM
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="pcm"
            )

            # Base64 encode PCM bytes
            encoded_audio = base64.b64encode(response.content).decode('utf-8')

            print(f"✅ Generated {len(encoded_audio)} bytes")
            return encoded_audio

        except Exception as e:
            print(f"❌ TTS Error: {e}")
            import traceback
            traceback.print_exc()
            return ""
