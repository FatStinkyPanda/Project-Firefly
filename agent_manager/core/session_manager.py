from collections import deque
from typing import List, Dict, Any, Optional
import logging
import time

logger = logging.getLogger("FireflySessionManager")

class SessionManager:
    """
    Manages stateful conversation histories for different trigger sources.
    Ensures agents have context of previous turns.
    """
    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.sessions: Dict[str, deque] = {} # session_id -> deque of message dicts

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Returns the chat history for a given session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = deque(maxlen=self.max_history)
        return list(self.sessions[session_id])

    def add_message(self, session_id: str, role: str, content: str):
        """Adds a message to the session history."""
        if session_id not in self.sessions:
            self.sessions[session_id] = deque(maxlen=self.max_history)

        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        logger.debug(f"Added {role} message to session {session_id}")

    def clear_session(self, session_id: str):
        """Resets the history for a session."""
        if session_id in self.sessions:
            self.sessions[session_id].clear()
            logger.info(f"Cleared session: {session_id}")

    def format_for_ai(self, session_id: str) -> str:
        """Formats the history as a single string for AI context (compatibility mode)."""
        history = self.get_history(session_id)
        if not history:
            return ""

        formatted = "\n--- CONVERSATION HISTORY ---\n"
        for msg in history:
            formatted += f"{msg['role'].upper()}: {msg['content']}\n"
        formatted += "--- END HISTORY ---\n"
        return formatted
