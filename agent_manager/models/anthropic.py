from typing import Optional, TYPE_CHECKING, Dict, Any
import json
import logging
import os
import urllib.error
import urllib.request

from .base import BaseHandler
from __future__ import annotations

if TYPE_CHECKING:
    from .base import BaseHandler
from __future__ import annotations

logger = logging.getLogger("FireflyAnthropicHandler")

class AnthropicHandler(BaseHandler):
    """
    Anthropic Service (Claude) using standard library (zero-dependency).
    """
    BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: Optional[str] = None, model_name: str = "claude-3-5-sonnet-20240620"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model_name = model_name

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> HandlerResponse:
        from .base import HandlerResponse
        if not self.validate_config():
            raise ValueError("Anthropic API Key not found. Set ANTHROPIC_API_KEY environment variable.")

        # Construct payload
        data = {
            "model": self.model_name,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            data["system"] = system_prompt

        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01'
        }

        req = urllib.request.Request(self.BASE_URL, data=json.dumps(data).encode('utf-8'), headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))

                try:
                    # Anthropic returns a list of content blocks
                    text = ""
                    for block in result.get("content", []):
                        if block.get("type") == "text":
                            text += block.get("text", "")

                    usage = result.get('usage', {})
                    pt = usage.get('input_tokens', 0)
                    ct = usage.get('output_tokens', 0)

                    # Estimate cost (Claude 3.5 Sonnet approx)
                    # $3 / 1M input, $15 / 1M output
                    cost = (pt * 0.000003) + (ct * 0.000015)

                    return HandlerResponse(
                        text=text.strip(),
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        model_name=self.model_name,
                        cost_usd=cost,
                        metadata={"raw_usage": usage}
                    )
                except (KeyError, IndexError):
                     logger.error(f"Unexpected Anthropic response format: {result}")
                     raise ValueError("Failed to parse Anthropic response")

        except urllib.error.HTTPError as e:
            logger.error(f"Anthropic API Error: {e.code} - {e.reason}")
            # Try to read error body
            try:
                err_body = e.read().decode('utf-8')
                logger.error(f"Error body: {err_body}")
            except: pass
            raise Exception(f"Anthropic API failed with status {e.code}")
        except Exception as e:
            logger.error(f"Anthropic Connection Error: {e}")
            raise
