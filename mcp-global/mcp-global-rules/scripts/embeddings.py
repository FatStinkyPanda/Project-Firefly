"""
Embeddings Generation
=====================
Generate vector embeddings for code semantic search.
Uses sentence-transformers or falls back to TF-IDF.

Usage:
    from scripts.embeddings import embed_text, embed_code
"""

import sys
import re
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .utils import Console


# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Try to import numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


# Model cache
_model = None
_model_name = "all-MiniLM-L6-v2"  # 22MB, good quality/speed balance


def get_model():
    """Get or load embedding model."""
    global _model

    if _model is not None:
        return _model

    if not TRANSFORMERS_AVAILABLE:
        return None

    try:
        # Try to load from local cache first
        _model = SentenceTransformer(_model_name)
        return _model
    except Exception as e:
        Console.warn(f"Could not load embedding model: {e}")
        return None


def embed_text(text: str) -> Optional[List[float]]:
    """Generate embedding for text."""
    model = get_model()

    if model is not None:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    # Fallback to simple TF-IDF-like embedding
    return _fallback_embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    model = get_model()

    if model is not None:
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    # Fallback
    return [_fallback_embed(t) for t in texts]


def embed_code(code: str, language: str = "python") -> Optional[List[float]]:
    """Generate embedding for code with language-aware preprocessing."""
    # Preprocess code for better embeddings
    processed = _preprocess_code(code, language)
    return embed_text(processed)


def _preprocess_code(code: str, language: str) -> str:
    """Preprocess code for embedding."""
    # Remove comments based on language
    if language in ('python', 'ruby'):
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    elif language in ('javascript', 'typescript', 'java', 'c', 'cpp', 'go', 'rust'):
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

    # Normalize whitespace
    code = ' '.join(code.split())

    # Split camelCase and snake_case for better semantic matching
    code = re.sub(r'([a-z])([A-Z])', r'\1 \2', code)
    code = code.replace('_', ' ')

    return code.lower()


def _fallback_embed(text: str, dim: int = 384) -> List[float]:
    """Simple fallback embedding using hashing + TF-IDF-like approach."""
    # Tokenize
    tokens = re.findall(r'[a-z0-9]+', text.lower())

    if not tokens:
        return [0.0] * dim

    # Create embedding via feature hashing
    embedding = [0.0] * dim

    for token in tokens:
        # Hash token to get index
        h = hash(token)
        idx = abs(h) % dim

        # Add weighted value
        tf = tokens.count(token) / len(tokens)
        embedding[idx] += tf

    # Normalize
    norm = math.sqrt(sum(x * x for x in embedding))
    if norm > 0:
        embedding = [x / norm for x in embedding]

    return embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def embedding_dimension() -> int:
    """Get embedding dimension."""
    model = get_model()
    if model is not None:
        return model.get_sentence_embedding_dimension()
    return 384  # Fallback dimension


def is_transformers_available() -> bool:
    """Check if sentence-transformers is available."""
    return TRANSFORMERS_AVAILABLE


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    method: str  # 'transformer' or 'fallback'


def embed_with_info(text: str) -> EmbeddingResult:
    """Generate embedding with metadata."""
    model = get_model()

    if model is not None:
        embedding = model.encode(text, convert_to_numpy=True).tolist()
        return EmbeddingResult(text=text, embedding=embedding, method='transformer')

    embedding = _fallback_embed(text)
    return EmbeddingResult(text=text, embedding=embedding, method='fallback')


def main():
    """CLI entry point."""
    Console.header("Embedding Generation")

    if TRANSFORMERS_AVAILABLE:
        Console.ok("sentence-transformers available")
        model = get_model()
        if model:
            Console.ok(f"Model: {_model_name}")
            Console.ok(f"Dimension: {embedding_dimension()}")
    else:
        Console.warn("sentence-transformers not available, using fallback")
        Console.info(f"Fallback dimension: 384")

    # Test embedding
    args = [a for a in sys.argv[1:] if not a.startswith('-')]

    if args:
        text = ' '.join(args)
        Console.info(f"Embedding: {text[:50]}...")

        result = embed_with_info(text)
        Console.ok(f"Method: {result.method}")
        Console.ok(f"Dimension: {len(result.embedding)}")
        Console.ok(f"Sample values: {result.embedding[:5]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
