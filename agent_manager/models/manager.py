from typing import List, Optional
import logging

from .base import BaseModelService
from .gemini import GeminiService
from .openai import OpenAIService

logger = logging.getLogger("FireflyModelClient")

class ModelClientManager:
    """
    Universal Model Client.
    Manages multiple model services and handles failover logic.
    """
    def __init__(self, providers: Optional[List[BaseModelService]] = None):
        self.providers = providers or []
        if not self.providers:
            # Default fallback chain if none provided
            # Note: In production, these should be configured via config files/env
            try:
                self.providers.append(GeminiService())
            except Exception:
                pass

            try:
                self.providers.append(OpenAIService())
            except Exception:
                pass

        if not self.providers:
            logger.warning("No model services configured or initialized successfully.")

    def add_provider(self, provider: BaseModelService):
        """Add a service to the end of the priority list."""
        self.providers.append(provider)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
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
                return response

            except Exception as e:
                error_msg = f"{provider_name} failed: {str(e)}"
                logger.error(error_msg)
                full_error_log.append(error_msg)
                # Continue to next provider

        # If we reach here, all providers failed
        raise RuntimeError(f"All model providers failed: {'; '.join(full_error_log)}")
