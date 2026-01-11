from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class TagResponse:
    """
    Structured container for parsed tags.
    """
    thoughts: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    status_updates: List[str] = field(default_factory=list)
    calls: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""

    def has_actions(self) -> bool:
        return len(self.commands) > 0 or len(self.calls) > 0
