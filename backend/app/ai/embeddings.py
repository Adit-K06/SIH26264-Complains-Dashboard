"""Optional neural sentence embeddings for complaint similarity.

Design rules (so nothing else in the backend changes or breaks):
  * Nothing here is imported at module load by the frozen contract; heavy libraries are
    imported lazily, only when an embedding mode is actually requested.
  * If `sentence-transformers` or the model is unavailable, `get_embedder()` returns None and
    callers fall back to TF-IDF. The scan never fails because a model is missing.
  * Texts are embedded once and cached, so a scan over N cases costs N encodes, not N^2.

Environment variables
  SIMILARITY_MODE   tfidf (default) | hybrid | embedding
  EMBEDDING_MODEL   sentence-transformers model name or local path
                    (default: sentence-transformers/all-MiniLM-L6-v2; use a multilingual model
                    such as paraphrase-multilingual-MiniLM-L12-v2 for Hindi/regional text)
  EMBEDDING_FLOOR   cosine value treated as "unrelated" when rescaling to 0..1 (default 0.30)
"""
from __future__ import annotations

import os
import re
import threading
from typing import Callable, Iterable, Optional

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VALID_MODES = ("tfidf", "hybrid", "embedding")


def similarity_mode() -> str:
    mode = os.getenv("SIMILARITY_MODE", "tfidf").strip().lower()
    return mode if mode in VALID_MODES else "tfidf"


def embedding_floor() -> float:
    try:
        return min(0.95, max(0.0, float(os.getenv("EMBEDDING_FLOOR", "0.30"))))
    except ValueError:
        return 0.30


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


class Embedder:
    """Wraps any `encode_fn(list[str]) -> array[n, d]` with L2 normalisation and a text cache."""

    def __init__(self, encode_fn: Callable[[list], "np.ndarray"], name: str = "custom", cache_size: int = 50_000):
        self._encode_fn = encode_fn
        self.name = name
        self._cache: dict[str, np.ndarray] = {}
        self._cache_size = cache_size
        self._lock = threading.Lock()

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        items = [_clean(t) for t in texts]
        missing = [t for t in dict.fromkeys(items) if t not in self._cache]
        if missing:
            vectors = np.asarray(self._encode_fn(missing), dtype="float32")
            if vectors.ndim != 2 or vectors.shape[0] != len(missing):
                raise ValueError("embedding function returned an unexpected shape")
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.where(norms == 0, 1.0, norms)
            with self._lock:
                if len(self._cache) + len(missing) > self._cache_size:
                    self._cache.clear()
                for text, vec in zip(missing, vectors):
                    self._cache[text] = vec
        dim = next(iter(self._cache.values())).shape[0] if self._cache else 0
        return np.vstack([self._cache.get(t, np.zeros(dim, dtype="float32")) for t in items]) if items else np.zeros((0, dim))

    def cosine(self, a: str, b: str) -> float:
        if not _clean(a) or not _clean(b):
            return 0.0
        va, vb = self.encode([a, b])
        return float(np.dot(va, vb))


_embedder: Optional[Embedder] = None
_load_failed = False
_load_lock = threading.Lock()


def set_embedder(embedder: Optional[Embedder]) -> None:
    """Inject an embedder (tests, or an app that already holds a model). None resets to lazy-load."""
    global _embedder, _load_failed
    with _load_lock:
        _embedder = embedder
        _load_failed = False


def get_embedder() -> Optional[Embedder]:
    """Return the shared embedder, loading the sentence-transformers model on first use.

    Returns None (and remembers the failure) if the library or model cannot be loaded.
    """
    global _embedder, _load_failed
    if _embedder is not None or _load_failed:
        return _embedder
    with _load_lock:
        if _embedder is not None or _load_failed:
            return _embedder
        try:
            from sentence_transformers import SentenceTransformer  # lazy: heavy import
            model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
            model = SentenceTransformer(model_name)
            _embedder = Embedder(
                lambda texts: model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True),
                name=model_name,
            )
        except Exception:  # ImportError, offline model download, OOM ... -> fall back to TF-IDF
            _load_failed = True
            _embedder = None
    return _embedder


def embedding_similarity(a: str, b: str, embedder: Optional[Embedder] = None) -> Optional[float]:
    """Calibrated 0..1 semantic similarity, or None when no embedder is available.

    Raw cosine of sentence embeddings is rarely near 0 for two complaints in the same domain
    (typically 0.2-0.4 for unrelated ones), so it is rescaled with EMBEDDING_FLOOR:
    (cos - floor) / (1 - floor), clipped to [0, 1]. Without this, same-category cases would
    all look partly similar and inflate Tier B flags.
    """
    embedder = embedder or get_embedder()
    if embedder is None:
        return None
    cos = embedder.cosine(a, b)
    floor = embedding_floor()
    return float(min(1.0, max(0.0, (cos - floor) / (1.0 - floor))))
