from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional, Dict, Any

@dataclass
class ServiceResponse:
    """
    Standardized response from an AI Model Service.
    """
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_name: str = "unknown"
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseService(ABC):
    """
    Abstract base class for all LLM providers.
    Enforces a consistent interface for the ModelConnectionManager.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "default"):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> ServiceResponse:
        """
        Generate a complete response from the model.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instruction.

        Returns:
            ServiceResponse: The generated text and usage metadata.

        Raises:
            Exception: If the API call fails.
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Check if the provider is correctly configured (e.g., has API key).
        """
        pass
