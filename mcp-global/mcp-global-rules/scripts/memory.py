"""
Persistent Memory System
========================
Cross-session knowledge base for AI agents.

Usage:
    python mcp.py remember "key" "value"
    python mcp.py recall "query"
    python mcp.py forget "key"
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import json
import sys

from .embeddings import embed_text, cosine_similarity
from .utils import Console, find_project_root


@dataclass
class Memory:
    """A memory item."""
    key: str
    value: str
    tags: List[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    access_count: int = 0
    embedding: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        return cls(**data)


class MemoryStore:
    """Persistent memory storage."""

    def __init__(self, storage_path: Path = None):
        if storage_path:
            self.storage_path = storage_path
        else:
            # Use user-level storage for cross-project memory
            home = Path.home()
            self.storage_path = home / '.mcp' / 'memory'

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.memories: Dict[str, Memory] = {}
        self.load()

    def _get_file_path(self) -> Path:
        return self.storage_path / 'knowledge.json'

    def load(self):
        """Load memories from disk."""
        file_path = self._get_file_path()
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = {k: Memory.from_dict(v) for k, v in data.items()}
            except Exception:
                self.memories = {}

    def save(self):
        """Save memories to disk."""
        file_path = self._get_file_path()
        with open(file_path, 'w', encoding='utf-8') as f:
            data = {k: v.to_dict() for k, v in self.memories.items()}
            json.dump(data, f, indent=2)

    def remember(self, key: str, value: str, tags: List[str] = None) -> Memory:
        """Store a memory."""
        now = datetime.utcnow().isoformat() + 'Z'

        # Generate embedding for semantic search
        combined = f"{key} {value}"
        embedding = embed_text(combined) or []

        if key in self.memories:
            # Update existing
            memory = self.memories[key]
            memory.value = value
            memory.updated = now
            memory.tags = tags or memory.tags
            memory.embedding = embedding
        else:
            # Create new
            memory = Memory(
                key=key,
                value=value,
                tags=tags or [],
                created=now,
                updated=now,
                embedding=embedding
            )

        self.memories[key] = memory
        self.save()
        return memory

    def recall(self, query: str, limit: int = 10) -> List[Memory]:
        """Search memories semantically."""
        if not self.memories:
            return []

        # Generate query embedding
        query_emb = embed_text(query)

        results = []
        for key, memory in self.memories.items():
            # Update access count
            memory.access_count += 1

            # Calculate relevance score
            score = 0.0

            # Exact key match
            if query.lower() in key.lower():
                score += 1.0

            # Value match
            if query.lower() in memory.value.lower():
                score += 0.5

            # Tag match
            for tag in memory.tags:
                if query.lower() in tag.lower():
                    score += 0.3

            # Semantic similarity
            if query_emb and memory.embedding:
                semantic_score = cosine_similarity(query_emb, memory.embedding)
                score += semantic_score * 0.5

            if score > 0:
                results.append((memory, score))

        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)

        self.save()  # Save access counts
        return [r[0] for r in results[:limit]]

    def forget(self, key: str) -> bool:
        """Remove a memory."""
        if key in self.memories:
            del self.memories[key]
            self.save()
            return True
        return False

    def list_all(self, tag: str = None) -> List[Memory]:
        """List all memories, optionally filtered by tag."""
        if tag:
            return [m for m in self.memories.values() if tag in m.tags]
        return list(self.memories.values())

    def get_by_key(self, key: str) -> Optional[Memory]:
        """Get memory by exact key."""
        return self.memories.get(key)

    def export_all(self) -> str:
        """Export all memories as JSON."""
        return json.dumps({k: v.to_dict() for k, v in self.memories.items()}, indent=2)

    def import_memories(self, json_str: str) -> int:
        """Import memories from JSON."""
        try:
            data = json.loads(json_str)
            count = 0
            for key, mem_data in data.items():
                if key not in self.memories:
                    self.memories[key] = Memory.from_dict(mem_data)
                    count += 1
            self.save()
            return count
        except Exception:
            return 0


# Global store instance
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    """Get or create memory store."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def remember(key: str, value: str, tags: List[str] = None) -> Memory:
    """Store a memory."""
    return get_store().remember(key, value, tags)


def recall(query: str, limit: int = 10) -> List[Memory]:
    """Search memories."""
    return get_store().recall(query, limit)


def forget(key: str) -> bool:
    """Forget a memory."""
    return get_store().forget(key)


def main():
    """CLI entry point."""
    Console.header("Persistent Memory")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    store = get_store()

    Console.info(f"Memory storage: {store.storage_path}")
    Console.info(f"Total memories: {len(store.memories)}")

    if len(args) >= 2:
        key = args[0]
        value = args[1]
        tags = args[2:] if len(args) > 2 else []

        memory = store.remember(key, value, tags)
        Console.ok(f"Remembered: {key}")
        print(f"  Value: {value}")
        if tags:
            print(f"  Tags: {', '.join(tags)}")
        return 0

    if len(args) == 1:
        query = args[0]

        if '--forget' in sys.argv or '--delete' in sys.argv:
            if store.forget(query):
                Console.ok(f"Forgot: {query}")
            else:
                Console.warn(f"Not found: {query}")
            return 0

        # Search
        Console.info(f"Recalling: {query}")
        results = store.recall(query)

        if results:
            for mem in results:
                print(f"\n  [{mem.key}]")
                print(f"  {mem.value}")
                if mem.tags:
                    print(f"  Tags: {', '.join(mem.tags)}")
        else:
            Console.warn("No matching memories")
        return 0

    # List all
    if '--list' in sys.argv or not args:
        memories = store.list_all()
        Console.info(f"All memories ({len(memories)}):")
        for mem in memories[:20]:
            print(f"  [{mem.key}] {mem.value[:50]}...")

    if '--export' in sys.argv:
        print(store.export_all())

    return 0


if __name__ == "__main__":
    sys.exit(main())
