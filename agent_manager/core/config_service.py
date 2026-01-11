from pathlib import Path
from typing import Dict, Any, List
import json
import logging
import os

logger = logging.getLogger("FireflyConfigService")

class ConfigurationService:
    """
    Manages Firefly options and policies.
    """
    DEFAULT_CONFIG = {
        "model_priority": ["gemini", "openai", "anthropic", "openrouter", "ollama"],
        "approval_policy": "ORCHESTRATOR_ONLY",  # AUTO, ORCHESTRATOR_ONLY, MANUAL
        "auto_approved_commands": [
            "ls", "pwd", "git status", "git diff", "cat", "mcp.py context", "mcp.py search"
        ],
        "orchestrator_approved_commands": [
            "git add", "git commit", "git push", "git merge", "git checkout", "git branch", "mcp.py fix", "mcp.py review", "npm test", "pytest"
        ],
        "always_ask_commands": [
            "rm -rf", "format C:", "del /s", "curl -X POST", "sh", "bash", "powershell"
        ],
        "git_agent_always_live": False
    }

    def __init__(self, config_path: str = "options.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            logger.info(f"Config file not found. Creating default at {self.config_path}")
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}. Using defaults.")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self, config: Dict[str, Any]):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save_config(self.config)

    def is_command_safe(self, command: str, agent_context: str = "default") -> bool:
        """
        Check if a command is approved based on the current policy.
        """
        policy = self.get("approval_policy", "MANUAL")

        if policy == "AUTO":
            # Still check against 'always_ask' for extreme safety
            if any(forbidden in command.lower() for forbidden in self.get("always_ask_commands", [])):
                 return False
            return True

        # Check if explicitly auto-approved
        if any(cmd in command for cmd in self.get("auto_approved_commands", [])):
            return True

        if policy == "ORCHESTRATOR_ONLY":
            if agent_context == "orchestrator":
                # Check if it's in the orchestrator-approved list
                if any(cmd in command for cmd in self.get("orchestrator_approved_commands", [])):
                    return True

        return False
