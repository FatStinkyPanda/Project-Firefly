from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging
import os

import faiss
import numpy as np

logger = logging.getLogger("FireflyMemoryService")

class MemoryService:
    """
    Project-Firefly Semantic Memory.
    Uses FAISS for vector search and an LLM for embeddings.
    Indexes thoughts, commands, and code context.
    """
    def __init__(self, model_client, memory_path: Optional[str] = None):
        self.model_client = model_client
        self.root_path = Path(memory_path or ".firefly/memory")
        self.index_file = self.root_path / "firefly_index.faiss"
        self.metadata_file = self.root_path / "firefly_metadata.json"

        self.dimension = 1536 # Default for OpenAI 'text-embedding-3-small'
        self.index = None
        self.metadata = [] # List of dicts matching index IDs

        self._initialize_storage()

    def _initialize_storage(self):
        self.root_path.mkdir(parents=True, exist_ok=True)
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Memory loaded: {len(self.metadata)} items.")
            except Exception as e:
                logger.error(f"Failed to load memory index: {e}")
                self._create_empty_index()
        else:
            self._create_empty_index()

    def _create_empty_index(self):
        # We start with FlatL2 for simplicity.
        # For very large codebases, HNSW is better.
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        logger.info("Created new empty memory index.")

    def upsert(self, text: str, meta: Dict[str, Any]):
        """Vectorize and store text in the index."""
        try:
            embedding = self.model_client.embed(text)
            vec = np.array([embedding]).astype('float32')

            # If dimensions mismatch (e.g. model changed), reset index
            if vec.shape[1] != self.dimension:
                logger.warning(f"Embedding dimension mismatch ({vec.shape[1]} vs {self.dimension}). Recreating index.")
                self.dimension = vec.shape[1]
                self._create_empty_index()
                # Retry once
                return self.upsert(text, meta)

            self.index.add(vec)
            self.metadata.append({
                "text": text,
                **meta
            })
            self.save()
            return True
        except Exception as e:
            logger.error(f"Failed to upsert memory: {e}")
            return False

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search memory for relevant context."""
        if self.index.ntotal == 0:
            return []

        try:
            embedding = self.model_client.embed(query_text)
            vec = np.array([embedding]).astype('float32')

            distances, indices = self.index.search(vec, top_k)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.metadata):
                    res = self.metadata[idx].copy()
                    res["score"] = float(distances[0][i])
                    results.append(res)
            return results
        except Exception as e:
            logger.error(f"Failed to query memory: {e}")
            return []

    def save(self):
        """Persist index and metadata to disk."""
        try:
            faiss.write_index(self.index, str(self.index_file))
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
