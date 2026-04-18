try:
    import torch
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    torch = None
    SentenceTransformer = None

from typing import List, Union


class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence_transformers not installed. Run: pip install sentence-transformers torch")
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(texts, str):
            return self.model.encode(texts).tolist()
        else:
            return self.model.encode(texts).tolist()

    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


# Global embedding model instance (lazy initialization)
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            _embedding_model = EmbeddingModel()
        else:
            raise ImportError("sentence_transformers not installed")
    return _embedding_model

def get_embedding(text: str) -> List[float]:
    """Get embedding for a text string"""
    return _get_embedding_model().encode(text)