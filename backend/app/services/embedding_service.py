import logging
from typing import Optional, Any
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)

_model_instance: Optional[Any] = None


def get_embedding_model(model_name: Optional[str] = None) -> Any:
    """
    Lazy-loads and caches the SentenceTransformer embedding model singleton.
    Reuses the model in-memory across all incoming requests.
    """
    global _model_instance
    if _model_instance is None:
        target_model = model_name or settings.EMBEDDING_MODEL_NAME
        logger.info(f"Loading SentenceTransformer embedding model: {target_model}")
        from sentence_transformers import SentenceTransformer
        _model_instance = SentenceTransformer(target_model)
    return _model_instance


def set_embedding_model_override(model: Optional[Any]) -> None:
    """
    Overrides the singleton model instance for unit testing / mocking.
    """
    global _model_instance
    _model_instance = model


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculates the cosine similarity between two 1D or 2D vector arrays.
    Returns a float in range [-1.0, 1.0].
    """
    v1 = np.asarray(vec1, dtype=np.float32).flatten()
    v2 = np.asarray(vec2, dtype=np.float32).flatten()

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    dot = np.dot(v1, v2)
    return float(dot / (norm1 * norm2))


def compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Computes semantic text similarity using the local embedding model and cosine similarity.
    Returns normalized float in [0.0, 1.0].
    """
    if not text1.strip() or not text2.strip():
        return 0.0

    model = get_embedding_model()
    embeddings = model.encode([text1, text2])
    cos_sim = compute_cosine_similarity(embeddings[0], embeddings[1])

    # Normalize similarity to [0.0, 1.0]
    return max(0.0, min(1.0, cos_sim))
