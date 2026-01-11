from typing import Optional, TYPE_CHECKING, Dict, Any
import json
import logging
import os
import urllib.error
import urllib.request

from .base import BaseModelService
from __future__ import annotations

if TYPE_CHECKING:
    from .base import ModelResponse

logger = logging.getLogger("FireflyOpenRouterService")

class OpenRouterService(BaseModelService):
    """
    OpenRouter Service using standard library (zero-dependency).
    """
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model_name: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.model_name = model_name

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ModelResponse:
        from .base import ModelResponse
        if not self.validate_config():
            raise ValueError("OpenRouter API Key not found. Set OPENROUTER_API_KEY environment variable.")

        # Construct payload
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name,
            "messages": messages,
            "top_p": 1,
            "temperature": 0.7
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'HTTP-Referer': 'https://github.com/FatStinkyPanda/Project-Firefly',
            'X-Title': 'Firefly Agent Manager'
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

                    # Cost is provided by OpenRouter sometimes, but we'll fallback to 0.0
                    # if not explicitly calculated per model here.
                    cost = result.get('cost', 0.0)

                    return ModelResponse(
                        text=text.strip(),
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        model_name=self.model_name,
                        cost_usd=cost,
                        metadata={"raw_usage": usage}
                    )
                except (KeyError, IndexError):
                     logger.error(f"Unexpected OpenRouter response format: {result}")
                     raise ValueError("Failed to parse OpenRouter response")

        except urllib.error.HTTPError as e:
            logger.error(f"OpenRouter API Error: {e.code} - {e.reason}")
            raise Exception(f"OpenRouter API failed with status {e.code}")
        except Exception as e:
            logger.error(f"OpenRouter Connection Error: {e}")
            raise
