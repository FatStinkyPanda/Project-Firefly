from typing import Optional, TYPE_CHECKING, Dict, Any
import json
import logging
import urllib.error
import urllib.request

from .base import BaseModelService
from __future__ import annotations

if TYPE_CHECKING:
    from .base import ModelResponse

logger = logging.getLogger("FireflyOllamaService")

class OllamaService(BaseModelService):
    """
    Ollama Service for local inference (zero-dependency).
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "llama3", base_url: str = "http://localhost:11434/api/generate"):
        self.api_key = api_key # Usually none for local
        self.model_name = model_name
        self.base_url = base_url

    def validate_config(self) -> bool:
        # Check if ollama is reachable? For now just return True.
        return True

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ModelResponse:
        from .base import ModelResponse

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        data = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False
        }

        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(self.base_url, data=json.dumps(data).encode('utf-8'), headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))

                try:
                    text = result.get('response', "")

                    # Ollama counts
                    pt = result.get('prompt_eval_count', 0)
                    ct = result.get('eval_count', 0)

                    return ModelResponse(
                        text=text.strip(),
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        model_name=self.model_name,
                        cost_usd=0.0, # Local is free!
                        metadata={"raw": result}
                    )
                except Exception as e:
                     logger.error(f"Unexpected Ollama response format: {result}")
                     raise ValueError("Failed to parse Ollama response")

        except urllib.error.URLError as e:
            logger.error(f"Ollama Connection Error (Is ollama serve running?): {e}")
            raise Exception("Ollama service unreachable")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
