"""Text embeddings for semantic document search, alongside BM25 in app/knowledge.py.

Providers: a local ONNX model through fastembed (free, offline after the first model download) or any
OpenAI-compatible /embeddings endpoint (e.g. Ollama with nomic-embed-text, or OpenAI). Any failure returns None
and search falls back to BM25 alone, so the app keeps working without embeddings.
"""
import logging

import numpy as np

from . import config

log = logging.getLogger("sitebrain.embeddings")
_state: dict = {}  # "model" -> loaded fastembed model / openai client, "failed" -> reason embeddings are off


def provider() -> str | None:
    p = config.EMBED_PROVIDER
    if p == "off":
        return None
    if p in ("local", "openai_compat"):
        return p
    try:  # auto: local when fastembed is installed
        import fastembed  # noqa: F401
        return "local"
    except ImportError:
        return None


def model_name() -> str | None:
    return {"local": config.EMBED_MODEL, "openai_compat": config.EMBED_OPENAI_MODEL}.get(provider())


def available() -> bool:
    return bool(provider()) and "failed" not in _state


def status() -> dict:
    on = available()
    return {"enabled": on, "provider": provider() if on else None, "model": model_name() if on else None,
            "reason": _state.get("failed")}


def _client():
    if "model" not in _state:
        if provider() == "local":
            from fastembed import TextEmbedding
            _state["model"] = TextEmbedding(config.EMBED_MODEL)
        else:
            from openai import OpenAI
            _state["model"] = OpenAI(base_url=config.EMBED_OPENAI_BASE_URL, api_key=config.EMBED_OPENAI_API_KEY)
    return _state["model"]


def embed(texts: list[str], query: bool = False) -> np.ndarray | None:
    """Unit-length float32 vectors, one row per text, or None when embeddings are unavailable."""
    if not texts or not available():
        return None
    try:
        if provider() == "local":
            m = _client()
            vecs = list(m.query_embed(texts) if query else m.embed(texts, batch_size=32))
        else:
            res = _client().embeddings.create(model=config.EMBED_OPENAI_MODEL, input=texts)
            vecs = [d.embedding for d in res.data]
        arr = np.asarray(vecs, dtype=np.float32)
        return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-12)
    except Exception as e:  # model download blocked, server down, bad model name
        _state["failed"] = str(e)[:200]
        log.warning("embeddings switched off (%s); document search uses BM25 only", _state["failed"])
        return None


def to_bytes(v: np.ndarray) -> bytes:
    return v.astype(np.float32).tobytes()


def from_bytes(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)
