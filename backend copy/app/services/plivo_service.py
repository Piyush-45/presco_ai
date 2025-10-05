import os
import plivo
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class PlivoService:
    """Service to handle Plivo telephony operations"""

    def __init__(self):
        self.auth_id = os.getenv("PLIVO_AUTH_ID")
        self.auth_token = os.getenv("PLIVO_AUTH_TOKEN")
        self.phone_number = os.getenv("PLIVO_PHONE_NUMBER")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")

        # Initialize Plivo client
        if self.auth_id and self.auth_token:
            self.client = plivo.RestClient(self.auth_id, self.auth_token)
        else:
            self.client = None

    def validate_credentials(self):
        """Check if Plivo credentials are set"""
        if not all([self.auth_id, self.auth_token, self.phone_number]):
            raise ValueError("Plivo credentials not properly configured in .env")
        return True

    def make_call(self, to_number: str, call_id: int) -> Optional[str]:
        """
        Initiate outbound call to patient
        Returns: Plivo call UUID or None
        """
        if not self.client:
            raise ValueError("Plivo client not initialized")

        # Answer URL - Plivo will request this when call is answered
        answer_url = f"{self.base_url}/api/calls/answer/{call_id}"

        try:
            # Make the call
            response = self.client.calls.create(
                from_=self.phone_number,
                to_=to_number,
                answer_url=answer_url,
                answer_method='POST',
            )

            # Access response correctly - it's an object with direct attributes
            call_uuid = response.request_uuid
            print(f"✅ Call initiated: {call_uuid}")
            return call_uuid

        except plivo.exceptions.PlivoRestError as e:
            print(f"❌ Plivo error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error making call: {e}")
            return None

    @staticmethod
    def generate_answer_xml(websocket_url: str) -> str:
        """
        Generate Plivo XML response with Stream element
        This connects the call to our WebSocket for real-time audio
        """
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">
        {websocket_url}
    </Stream>
</Response>"""
        return xml
