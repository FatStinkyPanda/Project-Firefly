from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any

class BaseModelService(ABC):
    """
    Abstract Base Class for all AI Model Services.
    Enforces a consistent interface for the ModelClientManager.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "default"):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a complete response from the model.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instruction.

        Returns:
            The generated text string.

        Raises:
            Exception: If the API call fails (network, auth, rate limit).
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Check if the provider is correctly configured (e.g., has API key).
        """
        pass
