import os
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings

class EmbeddingService:
    def __init__(self):
        self.model = None

    def _load_model(self) -> SentenceTransformer:
        """Lazy load the sentence transformer model to prevent server start block."""
        if self.model is None:
            # SentenceTransformer automatically selects CUDA GPU if available, else CPU
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        return self.model

    def get_embedding(self, text: str) -> List[float]:
        """Generate a single embedding list of floats for a text string."""
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch for a list of text strings."""
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

embedding_service = EmbeddingService()
