from typing import Optional
import json
import logging
import os
import urllib.error
import urllib.request

from .base import BaseModelService

logger = logging.getLogger("FireflyGeminiService")

class GeminiService(BaseModelService):
    """
    Google Gemini Service using standard library (zero-dependency).
    """
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.validate_config():
            raise ValueError("Gemini API Key not found. Set GEMINI_API_KEY environment variable.")

        url = f"{self.BASE_URL}/{self.model_name}:generateContent?key={self.api_key}"

        # Construct payload
        contents = []
        if system_prompt:
             contents.append({"role": "user", "parts": [{"text": "System Instruction: " + system_prompt}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }

        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                # Parse response
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                     logger.error(f"Unexpected Gemini response format: {result}")
                     raise ValueError("Failed to parse Gemini response")

        except urllib.error.HTTPError as e:
            logger.error(f"Gemini API Error: {e.code} - {e.reason}")
            raise Exception(f"Gemini API failed with status {e.code}")
        except Exception as e:
            logger.error(f"Gemini Connection Error: {e}")
            raise
