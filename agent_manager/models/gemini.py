from typing import Optional, TYPE_CHECKING, Dict, Any, List
import json
import logging
import os
import urllib.error
import urllib.request

from .base import BaseService, ServiceResponse
from __future__ import annotations

logger = logging.getLogger("FireflyGeminiService")

class GeminiService(BaseService):
    """
    Google Gemini Service using standard library (zero-dependency).
    """
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ServiceResponse:
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

                try:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    usage = result.get('usageMetadata', {})
                    pt = usage.get('promptTokenCount', 0)
                    ct = usage.get('candidatesTokenCount', 0)

                    # Estimate cost (Gemini 1.5 Flash prices approx)
                    # $0.075 / 1M tokens prompt, $0.30 / 1M tokens completion
                    cost = (pt * 0.000000075) + (ct * 0.0000003)

                    return ServiceResponse(
                        text=text,
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        model_name=self.model_name,
                        cost_usd=cost,
                        metadata={"raw_usage": usage}
                    )
                except (KeyError, IndexError):
                     logger.error(f"Unexpected Gemini response format: {result}")
                     raise ValueError("Failed to parse Gemini response")

        except urllib.error.HTTPError as e:
            logger.error(f"Gemini API Error: {e.code} - {e.reason}")
            raise Exception(f"Gemini API failed with status {e.code}")
        except Exception as e:
            logger.error(f"Gemini Connection Error: {e}")
            raise

    def embed(self, text: str) -> List[float]:
        """Generate embedding using Google's Generative AI API."""
        if not self.api_key:
            raise ValueError("Gemini API Key not found.")

        # Using text-embedding-004 model for Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"

        data = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }

        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['embedding']['values']
        except Exception as e:
            logger.error(f"Gemini Embed Error: {e}")
            raise
