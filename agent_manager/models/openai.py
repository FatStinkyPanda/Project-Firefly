from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import json
import logging
import os
import urllib.error
import urllib.request

from .base import BaseModelService

logger = logging.getLogger("FireflyOpenAIService")

class OpenAIService(BaseModelService):
    """
    OpenAI Service using standard library (zero-dependency).
    """
    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ModelResponse:
        from .base import ModelResponse
        if not self.validate_config():
            raise ValueError("OpenAI API Key not found. Set OPENAI_API_KEY environment variable.")

        # Construct payload
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        req = urllib.request.Request(self.BASE_URL, data=json.dumps(data).encode('utf-8'), headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                try:
                    text = result['choices'][0]['message']['content']
                    usage = result.get('usage', {})
                    pt = usage.get('prompt_tokens', 0)
                    ct = usage.get('completion_tokens', 0)
                    
                    # Estimate cost (GPT-4o-mini prices approx)
                    # $0.15 / 1M tokens prompt, $0.60 / 1M tokens completion
                    cost = (pt * 0.00000015) + (ct * 0.0000006)

                    return ModelResponse(
                        text=text,
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        model_name=self.model_name,
                        cost_usd=cost,
                        metadata={"raw_usage": usage}
                    )
                except (KeyError, IndexError):
                     logger.error(f"Unexpected OpenAI response format: {result}")
                     raise ValueError("Failed to parse OpenAI response")

        except urllib.error.HTTPError as e:
            logger.error(f"OpenAI API Error: {e.code} - {e.reason}")
            raise Exception(f"OpenAI API failed with status {e.code}")
        except Exception as e:
            logger.error(f"OpenAI Connection Error: {e}")
            raise
