from __future__ import annotations
from typing import Optional, TYPE_CHECKING
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

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ModelResponse:
        from .base import ModelResponse
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

                    return ModelResponse(
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
