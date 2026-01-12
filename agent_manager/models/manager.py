from typing import List, Optional, Dict, Any
import logging

from .anthropic import AnthropicHandler
from .base import BaseHandler, HandlerResponse
from .gemini import GeminiHandler
from .ollama import OllamaHandler
from .open_connector import OpenRouterHandler
from .openai import OpenAIHandler

logger = logging.getLogger("FireflyHandlerClient")

class HandlerClientManager:
    """
    Universal Handler Client.
    Manages multiple model services and handles failover logic.
    Tracks token usage and cost.
    """
    def __init__(self, providers: Optional[List[BaseHandler]] = None, event_bus = None, config_service = None):
        self.providers = providers or []
        self.event_bus = event_bus
        self.config_service = config_service
        self.usage_ledger = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
            "by_model": {}
        }

        if not self.providers:
            # Default fallback chain if none provided
            self._initialize_default_providers()

        if self.config_service:
            self.reorder_providers()

        if not self.providers:
            logger.warning("No model services configured or initialized successfully.")

    def _initialize_default_providers(self):
        """Initialize all supported providers (keys loaded from env)."""
        for cls in [GeminiHandler, OpenAIHandler, AnthropicHandler, OpenRouterHandler, OllamaHandler]:
            try:
                p = cls()
                if p.validate_config():
                    self.providers.append(p)
            except Exception:
                pass

    def reorder_providers(self):
        """Reorder providers based on config priority."""
        priority_list = self.config_service.get("model_priority", [])
        if not priority_list:
            return

        def get_priority(p):
            # Map class name or model name to priority index
            name = p.__class__.__name__.lower().replace("service", "").replace("manager", "")
            try:
                return priority_list.index(name)
            except ValueError:
                return 999

        self.providers.sort(key=get_priority)
        logger.info(f"Handler providers reordered: {[p.__class__.__name__ for p in self.providers]}")

    def add_provider(self, provider: BaseHandler):
        """Add a service to the end of the priority list."""
        self.providers.append(provider)

    def _record_usage(self, response: HandlerResponse):
        """Update internal ledger and emit event."""
        self.usage_ledger["total_prompt_tokens"] += response.prompt_tokens
        self.usage_ledger["total_completion_tokens"] += response.completion_tokens
        self.usage_ledger["total_cost_usd"] += response.cost_usd

        m_name = response.model_name
        if m_name not in self.usage_ledger["by_model"]:
            self.usage_ledger["by_model"][m_name] = {"prompt": 0, "completion": 0, "cost": 0.0}

        self.usage_ledger["by_model"][m_name]["prompt"] += response.prompt_tokens
        self.usage_ledger["by_model"][m_name]["completion"] += response.completion_tokens
        self.usage_ledger["by_model"][m_name]["cost"] += response.cost_usd

        if self.event_bus:
            self.event_bus.publish("usage_report", {
                "current_response": {
                    "model": m_name,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "cost_usd": response.cost_usd
                },
                "total_usage": self.usage_ledger
            })

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> HandlerResponse:
        """
        Attempt to generate text using the configured providers in priority order.
        If one fails, try the next.
        """
        full_error_log = []

        for provider in self.providers:
            provider_name = f"{provider.__class__.__name__}({provider.model_name})"
            try:
                if not provider.validate_config():
                    logger.warning(f"Skipping {provider_name}: Invalid configuration (missing API key?)")
                    continue

                logger.info(f"Generating with {provider_name}...")
                response = provider.generate(prompt, system_prompt)
                logger.info(f"Success with {provider_name}")

                # Record usage
                self._record_usage(response)

                return response

            except Exception as e:
                error_msg = f"{provider_name} failed: {str(e)}"
                logger.error(error_msg)
                full_error_log.append(error_msg)
                # Continue to next provider

        # If we reach here, all providers failed
        raise RuntimeError(f"All model providers failed: {'; '.join(full_error_log)}")

    def embed(self, text: str) -> List[float]:
        """Generate an embedding for the text using the primary provider."""
        for provider in self.providers:
            try:
                return provider.embed(text)
            except Exception as e:
                logger.warning(f"Embedding failed with {provider.__class__.__name__}: {e}")
                continue
        raise RuntimeError("All embedding providers failed.")
