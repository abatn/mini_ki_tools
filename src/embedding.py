import torch
from sentence_transformers import SentenceTransformer
from typing import List, Union


class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        if isinstance(texts, str):
            return self.model.encode(texts).tolist()
        else:
            return self.model.encode(texts).tolist()

    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


# Global embedding model instance
embedding_model = EmbeddingModel()

def get_embedding(text: str) -> List[float]:
    """Get embedding for a text string"""
    return embedding_model.encode(text)