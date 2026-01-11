from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging
import re

from agent_manager.models.tag import TagResponse

logger = logging.getLogger("FireflyTagParser")


class TagParserService:
    """
    Robustly extracts structured data from AI-generated text using XML-like tags.
    Resilient to malformed JSON, interleaving, and surrounding noise.
    """
    TAG_PATTERNS = {
        "thought": r"<thought>(.*?)</thought>",
        "command": r"<command>(.*?)</command>",
        "message": r"<message>(.*?)</message>",
        "status": r"<status>(.*?)</status>",
        "call": r"<call>(.*?)</call>"
    }

    def parse(self, text: str) -> TagResponse:
        """
        Parse text and extract all identified tags.
        """
        # Clean up common AI artifacts like markdown code blocks around tags
        # e.g. ```xml <command>ls</command> ```
        text = re.sub(r"```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```", "", text)

        response = TagResponse(raw_text=text)

        # Extract standard tags
        response.thoughts = self._extract_all(text, "thought")
        response.commands = self._extract_all(text, "command")
        response.messages = self._extract_all(text, "message")
        response.status_updates = self._extract_all(text, "status")

        # Special handling for calls (might contain JSON inside tags)
        raw_calls = self._extract_all(text, "call")
        for raw in raw_calls:
            try:
                import json
                response.calls.append(json.loads(raw))
            except Exception:
                # If it's not JSON, just treat it as a raw call string
                response.calls.append({"raw": raw})

        return response

    def _extract_all(self, text: str, tag_name: str) -> List[str]:
        """
        Extract all occurrences of a specific tag using regex.
        Supports multiline content (DOTALL).
        """
        pattern = self.TAG_PATTERNS.get(tag_name)
        if not pattern:
            return []

        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [m.strip() for m in matches]

    @staticmethod
    def wrap(content: str, tag: str) -> str:
        """Utility to wrap content in FTS tags."""
        return f"<{tag}>\n{content}\n</tag>"
