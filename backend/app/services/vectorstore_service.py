import os
import faiss
import numpy as np
from typing import List, Tuple
from app.core.config import settings

# Directory to store vector files (relative to backend root)
VECTOR_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "vectorstore")
INDEX_PATH = os.path.join(VECTOR_DB_DIR, "index.faiss")
DIMENSION = 384  # paraphrase-multilingual-MiniLM-L12-v2 model size is 384

class VectorStoreService:
    def __init__(self):
        self.index = None
        self._init_index()

    def _init_index(self):
        """Load the FAISS index from disk if it exists, otherwise create a new one."""
        if not os.path.exists(VECTOR_DB_DIR):
            os.makedirs(VECTOR_DB_DIR)
            
        if os.path.exists(INDEX_PATH):
            try:
                self.index = faiss.read_index(INDEX_PATH)
            except Exception:
                # If reading fails (e.g. corruption), start a fresh index
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new IndexIDMap wrapping a Flat Inner Product index."""
        # IndexFlatIP calculates inner product.
        # When combined with L2 normalized vectors, this equals Cosine Similarity.
        quantizer = faiss.IndexFlatIP(DIMENSION)
        self.index = faiss.IndexIDMap(quantizer)
        self._save_index()

    def _save_index(self):
        """Persist index state to disk."""
        faiss.write_index(self.index, INDEX_PATH)

    def add_chunks(self, chunk_ids: List[int], embeddings: List[List[float]]):
        """
        Add a batch of embeddings mapped to their exact database DocumentChunk IDs.
        """
        if not chunk_ids or not embeddings:
            return
        
        ids_arr = np.array(chunk_ids, dtype=np.int64)
        embeddings_arr = np.array(embeddings, dtype=np.float32)
        
        # L2 normalization converts inner product search to cosine similarity search
        faiss.normalize_L2(embeddings_arr)
        
        self.index.add_with_ids(embeddings_arr, ids_arr)
        self._save_index()

    def remove_chunks(self, chunk_ids: List[int]):
        """
        Remove specified chunk IDs from the FAISS vector index.
        Used to prevent orphan vectors when documents are deleted.
        """
        if not chunk_ids:
            return
        ids_arr = np.array(chunk_ids, dtype=np.int64)
        self.index.remove_ids(ids_arr)
        self._save_index()

    def search(self, query_embedding: List[float], k: int = 5) -> List[Tuple[int, float]]:
        """
        Search the vector index for similar content.
        Returns a list of tuples: (chunk_id, similarity_score).
        Cosine similarity range: [-1, 1], where 1 is identical.
        """
        if self.index.ntotal == 0:
            return []
            
        q_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(q_vec)
        
        distances, indices = self.index.search(q_vec, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            # FAISS returns -1 for empty search slots (if ntotal < k)
            if idx != -1:
                results.append((int(idx), float(dist)))
        return results

# Initialize a global service singleton
vectorstore_service = VectorStoreService()
