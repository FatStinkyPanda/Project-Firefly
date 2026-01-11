"""
Vector Store
=============
Local FAISS-based vector database for semantic code search.

Usage:
    from scripts.vector_store import VectorStore

    store = VectorStore(path)
    store.index_codebase(root)
    results = store.search("authentication handler", k=10)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib

from .utils import Console, find_python_files, find_project_root
from .embeddings import embed_text, embed_texts, cosine_similarity, embedding_dimension


# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Try numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class CodeChunk:
    """A chunk of code with metadata."""
    id: str
    path: str
    content: str
    chunk_type: str  # 'function', 'class', 'file', 'block'
    line_start: int
    line_end: int
    language: str = ""
    name: str = ""


@dataclass
class SearchResult:
    """A search result."""
    chunk: CodeChunk
    score: float
    rank: int


class VectorStore:
    """Local vector store for semantic code search."""

    def __init__(self, index_path: Optional[Path] = None):
        if index_path is None:
            root = find_project_root() or Path.cwd()
            self.index_path = root / ".mcp" / "vector_index"
        else:
            self.index_path = Path(index_path)

        self.chunks: Dict[str, CodeChunk] = {}
        self.embeddings: Dict[str, List[float]] = {}
        self._faiss_index = None
        self._id_to_idx: Dict[str, int] = {}
        self._idx_to_id: Dict[int, str] = {}

    def index_codebase(self, root: Path, exclude_patterns: List[str] = None) -> int:
        """Index all code files in directory."""
        Console.info(f"Indexing {root}...")

        files = list(find_python_files(root, exclude_patterns))
        Console.info(f"Found {len(files)} files")

        chunks = []
        for path in files:
            file_chunks = self._extract_chunks(path)
            chunks.extend(file_chunks)

        Console.info(f"Extracted {len(chunks)} code chunks")

        if not chunks:
            return 0

        # Generate embeddings
        Console.info("Generating embeddings...")
        texts = [c.content[:1000] for c in chunks]  # Limit text length
        embeddings = embed_texts(texts)

        # Store chunks and embeddings
        for chunk, emb in zip(chunks, embeddings):
            self.chunks[chunk.id] = chunk
            self.embeddings[chunk.id] = emb

        # Build FAISS index if available
        if FAISS_AVAILABLE and NUMPY_AVAILABLE:
            self._build_faiss_index()

        # Save to disk
        self.save()

        Console.ok(f"Indexed {len(chunks)} chunks")
        return len(chunks)

    def _extract_chunks(self, path: Path) -> List[CodeChunk]:
        """Extract code chunks from file."""
        chunks = []

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return chunks

        # Detect language
        ext = path.suffix.lower()
        lang_map = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                    '.go': 'go', '.rs': 'rust', '.java': 'java'}
        language = lang_map.get(ext, 'unknown')

        # Create file-level chunk
        file_id = hashlib.md5(str(path).encode()).hexdigest()[:12]
        chunks.append(CodeChunk(
            id=f"{file_id}_file",
            path=str(path),
            content=content[:2000],  # First 2000 chars
            chunk_type='file',
            line_start=1,
            line_end=content.count('\n') + 1,
            language=language,
            name=path.name
        ))

        # Try to extract functions/classes using treesitter
        try:
            from .treesitter_utils import parse_file
            parsed = parse_file(path)

            lines = content.split('\n')

            for func in parsed.functions:
                func_content = '\n'.join(lines[func.line_start-1:func.line_end])
                chunks.append(CodeChunk(
                    id=f"{file_id}_func_{func.name}",
                    path=str(path),
                    content=func_content[:1000],
                    chunk_type='function',
                    line_start=func.line_start,
                    line_end=func.line_end,
                    language=language,
                    name=func.name
                ))

            for cls in parsed.classes:
                cls_content = '\n'.join(lines[cls.line_start-1:cls.line_end])
                chunks.append(CodeChunk(
                    id=f"{file_id}_class_{cls.name}",
                    path=str(path),
                    content=cls_content[:1000],
                    chunk_type='class',
                    line_start=cls.line_start,
                    line_end=cls.line_end,
                    language=language,
                    name=cls.name
                ))

        except Exception:
            pass  # Fall back to file-level only

        return chunks

    def _build_faiss_index(self):
        """Build FAISS index from embeddings."""
        if not self.embeddings:
            return

        dim = len(next(iter(self.embeddings.values())))

        # Create index
        self._faiss_index = faiss.IndexFlatIP(dim)  # Inner product = cosine for normalized

        # Add vectors
        ids = list(self.embeddings.keys())
        vectors = np.array([self.embeddings[id] for id in ids], dtype='float32')

        # Normalize for cosine similarity
        faiss.normalize_L2(vectors)

        self._faiss_index.add(vectors)

        # Build ID mappings
        for idx, id in enumerate(ids):
            self._id_to_idx[id] = idx
            self._idx_to_id[idx] = id

    def search(self, query: str, k: int = 10) -> List[SearchResult]:
        """Search for code matching query."""
        if not self.embeddings:
            return []

        # Generate query embedding
        query_emb = embed_text(query)
        if query_emb is None:
            return []

        # Use FAISS if available
        if self._faiss_index is not None and NUMPY_AVAILABLE:
            return self._faiss_search(query_emb, k)

        # Fallback to brute force
        return self._brute_force_search(query_emb, k)

    def _faiss_search(self, query_emb: List[float], k: int) -> List[SearchResult]:
        """Search using FAISS."""
        query_vec = np.array([query_emb], dtype='float32')
        faiss.normalize_L2(query_vec)

        k = min(k, len(self.embeddings))
        distances, indices = self._faiss_index.search(query_vec, k)

        results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:
                continue
            chunk_id = self._idx_to_id.get(int(idx))
            if chunk_id and chunk_id in self.chunks:
                results.append(SearchResult(
                    chunk=self.chunks[chunk_id],
                    score=float(dist),
                    rank=rank + 1
                ))

        return results

    def _brute_force_search(self, query_emb: List[float], k: int) -> List[SearchResult]:
        """Brute force cosine similarity search."""
        scores = []

        for chunk_id, emb in self.embeddings.items():
            score = cosine_similarity(query_emb, emb)
            scores.append((chunk_id, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for rank, (chunk_id, score) in enumerate(scores[:k]):
            if chunk_id in self.chunks:
                results.append(SearchResult(
                    chunk=self.chunks[chunk_id],
                    score=score,
                    rank=rank + 1
                ))

        return results

    def save(self):
        """Save index to disk."""
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Save chunks
        chunks_file = self.index_path / "chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.chunks.items()}, f)

        # Save embeddings
        emb_file = self.index_path / "embeddings.json"
        with open(emb_file, 'w', encoding='utf-8') as f:
            json.dump(self.embeddings, f)

        Console.ok(f"Index saved to {self.index_path}")

    def load(self) -> bool:
        """Load index from disk."""
        chunks_file = self.index_path / "chunks.json"
        emb_file = self.index_path / "embeddings.json"

        if not chunks_file.exists() or not emb_file.exists():
            return False

        try:
            with open(chunks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.chunks = {k: CodeChunk(**v) for k, v in data.items()}

            with open(emb_file, 'r', encoding='utf-8') as f:
                self.embeddings = json.load(f)

            if FAISS_AVAILABLE and NUMPY_AVAILABLE:
                self._build_faiss_index()

            Console.ok(f"Loaded {len(self.chunks)} chunks from index")
            return True

        except Exception as e:
            Console.warn(f"Could not load index: {e}")
            return False

    def update(self, changed_files: List[Path]):
        """Update index for changed files."""
        for path in changed_files:
            # Remove old chunks for this file
            to_remove = [k for k, v in self.chunks.items() if v.path == str(path)]
            for k in to_remove:
                del self.chunks[k]
                if k in self.embeddings:
                    del self.embeddings[k]

            # Re-index file
            if path.exists():
                new_chunks = self._extract_chunks(path)
                if new_chunks:
                    texts = [c.content[:1000] for c in new_chunks]
                    embeddings = embed_texts(texts)

                    for chunk, emb in zip(new_chunks, embeddings):
                        self.chunks[chunk.id] = chunk
                        self.embeddings[chunk.id] = emb

        # Rebuild FAISS index
        if FAISS_AVAILABLE and NUMPY_AVAILABLE:
            self._build_faiss_index()

        self.save()


def main():
    """CLI entry point."""
    Console.header("Vector Store")

    if FAISS_AVAILABLE:
        Console.ok("FAISS available")
    else:
        Console.warn("FAISS not available, using brute force search")

    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if len(args) < 1:
        Console.info("Usage: python vector_store.py <command> [args]")
        Console.info("Commands:")
        Console.info("  index <path>     Index codebase")
        Console.info("  search <query>   Search index")
        return 1

    command = args[0]
    store = VectorStore()

    if command == 'index':
        root = find_project_root() or Path.cwd()
        path = Path(args[1]) if len(args) > 1 else root
        store.index_codebase(path)

    elif command == 'search':
        query = ' '.join(args[1:]) if len(args) > 1 else ''
        if not query:
            Console.fail("No query provided")
            return 1

        # Load existing index
        if not store.load():
            Console.fail("No index found. Run 'index' first.")
            return 1

        Console.info(f"Searching: {query}")
        results = store.search(query, k=10)

        for r in results:
            print(f"\n[{r.rank}] {r.chunk.path}:{r.chunk.line_start} (score: {r.score:.3f})")
            print(f"    {r.chunk.chunk_type}: {r.chunk.name}")
            print(f"    {r.chunk.content[:100]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
