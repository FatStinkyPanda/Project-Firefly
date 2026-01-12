from pathlib import Path
from typing import Any, Dict, Optional
import json
import logging
import os
import time

logger = logging.getLogger("ArtifactService")

class ArtifactService:
    """
    Manages persistent storage of agent actions, thoughts, and results.
    Artifacts are stored in .firefly/artifacts/ organized by session and timestamp.
    """
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.artifact_base_dir = self.root_path / ".firefly" / "artifacts"
        self._ensure_dir()

    def _ensure_dir(self):
        """Ensures the artifact directory exists."""
        try:
            self.artifact_base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Artifact storage initialized at {self.artifact_base_dir}")
        except Exception as e:
            logger.error(f"Failed to create artifact directory: {e}")

    def create_artifact(self, session_id: str, artifact_type: str, content: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        Creates a new artifact entry.

        Args:
            session_id: The ID of the current agent session.
            artifact_type: The type of artifact (e.g., 'thought', 'command', 'browser_result').
            content: The data to store.
            metadata: Optional additional context.
        """
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        millis = int(time.time() * 1000) % 1000
        filename = f"{timestamp}-{millis}-{artifact_type}.json"

        session_dir = self.artifact_base_dir / session_id
        session_dir.mkdir(exist_ok=True)

        artifact_path = session_dir / filename

        data = {
            "timestamp": time.time(),
            "formatted_time": f"{timestamp}-{millis}",
            "type": artifact_type,
            "session_id": session_id,
            "content": content,
            "metadata": metadata or {}
        }

        try:
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Artifact created: {artifact_path}")
            return str(artifact_path)
        except Exception as e:
            logger.error(f"Failed to write artifact: {e}")
            return None

    def export_session_log(self, session_id: str):
        """
        Exports a consolidated markdown log for a specific session.
        """
        session_dir = self.artifact_base_dir / session_id
        if not session_dir.exists():
            return None

        artifacts = []
        for file in sorted(session_dir.glob("*.json")):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    artifacts.append(json.load(f))
            except Exception:
                continue

        if not artifacts:
            return None

        md_content = [f"# Session Log: {session_id}\n"]
        for art in artifacts:
            t = art.get("formatted_time")
            atype = art.get("type", "unknown").upper()
            content = art.get("content")

            md_content.append(f"## [{t}] {atype}")
            if isinstance(content, str):
                md_content.append(content)
            else:
                md_content.append(f"```json\n{json.dumps(content, indent=2)}\n```")
            md_content.append("\n---\n")

        log_path = session_dir / "session_summary.md"
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(md_content))
            return str(log_path)
        except Exception as e:
            logger.error(f"Failed to export session log: {e}")
            return None
