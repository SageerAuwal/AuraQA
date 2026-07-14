import os
import sys

# Ensure the backend directory is in the Python PATH
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.services.embedding_service import embedding_service
from app.services.vectorstore_service import vectorstore_service

def test_embedding_generation():
    print("Testing embedding generation (multilingual)...")
    texts = [
        "My favorite animal is the domestic cat.",
        "J'aime manger des pommes et des oranges.",  # French: I like to eat apples and oranges
        "الطقس جميل اليوم في القاهرة."  # Arabic: The weather is beautiful today in Cairo
    ]
    
    # Check dimensions
    embeddings = embedding_service.get_embeddings(texts)
    assert len(embeddings) == 3, f"Expected 3 embeddings, got {len(embeddings)}"
    
    for idx, emb in enumerate(embeddings):
        assert len(emb) == 384, f"Expected 384 dimensions, got {len(emb)} for index {idx}"
        
    print("[OK] Embedding generation and dimension checks passed.")
    return embeddings

def test_vectorstore_operations(embeddings):
    print("Testing FAISS vector store insertion, search, and cleanup...")
    # Reset/initialize index to clean testing state
    vectorstore_service._create_new_index()
    
    chunk_ids = [101, 102, 103]
    vectorstore_service.add_chunks(chunk_ids, embeddings)
    
    # 1. Verify index size
    assert vectorstore_service.index.ntotal == 3, f"Expected 3 vectors in index, got {vectorstore_service.index.ntotal}"
    print(f"Index now contains {vectorstore_service.index.ntotal} vectors.")
    
    # 2. English test: search for "felines"
    eng_query = embedding_service.get_embedding("felines and pets")
    results = vectorstore_service.search(eng_query, k=1)
    assert len(results) == 1, "Expected 1 search result"
    matched_id, score = results[0]
    assert matched_id == 101, f"Expected match with chunk 101, got {matched_id}"
    print(f"[OK] English search matched chunk {matched_id} with score {score:.4f}")
    
    # 3. Multilingual test: search in French for apples/fruits
    # Query: "Je veux manger des fruits" (I want to eat fruits)
    french_query = embedding_service.get_embedding("Je veux manger des fruits")
    results = vectorstore_service.search(french_query, k=1)
    assert len(results) == 1, "Expected 1 search result"
    matched_id, score = results[0]
    assert matched_id == 102, f"Expected match with French food chunk 102, got {matched_id}"
    print(f"[OK] French query matched English/French text (chunk {matched_id}) with score {score:.4f}")
    
    # 4. Multilingual test: search in Spanish for Cairo/weather
    # Query: "El clima es maravilloso hoy" (The weather is wonderful today)
    # Target chunk 103 (Arabic): "الطقس جميل اليوم في القاهرة" (The weather is beautiful today in Cairo)
    spanish_query = embedding_service.get_embedding("El clima es maravilloso hoy")
    results = vectorstore_service.search(spanish_query, k=1)
    assert len(results) == 1, "Expected 1 search result"
    matched_id, score = results[0]
    assert matched_id == 103, f"Expected match with Arabic weather chunk 103, got {matched_id}"
    print(f"[OK] Spanish query matched Arabic text (chunk {matched_id}) with score {score:.4f}")
    
    # 5. Clean up: remove ID 102
    print("Testing removing chunk from FAISS index...")
    vectorstore_service.remove_chunks([102])
    assert vectorstore_service.index.ntotal == 2, f"Expected 2 vectors left, got {vectorstore_service.index.ntotal}"
    
    # Check if searching for food now excludes deleted ID 102
    results = vectorstore_service.search(french_query, k=1)
    matched_id, score = results[0]
    assert matched_id != 102, "Deleted chunk 102 was still matched!"
    print("[OK] FAISS chunk deletion and search exclusion passed.")
    
    # Final cleanup of remaining vectors
    vectorstore_service.remove_chunks([101, 103])
    assert vectorstore_service.index.ntotal == 0, f"Expected empty index, got {vectorstore_service.index.ntotal}"
    print("[OK] Vector store operations verified.")

if __name__ == "__main__":
    print("=== Starting Phase 3 Integration Verification ===")
    try:
        embeddings = test_embedding_generation()
        test_vectorstore_operations(embeddings)
        print("=== Verification Successful! ===")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Verification failed: {e}", file=sys.stderr)
        sys.exit(1)
