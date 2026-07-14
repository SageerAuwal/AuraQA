import sys
import os
sys.path.append(r"c:\Users\HP ProBook\Desktop\ChatBot\backend")

from app.core.database import SessionLocal
from app.services.vectorstore_service import vectorstore_service
from app.services.embedding_service import embedding_service
from app.models.models import DocumentChunk

db = SessionLocal()
try:
    chunks = db.query(DocumentChunk).all()
    print(f"Total chunks in SQL DB: {len(chunks)}")
    if chunks:
        # Clear FAISS index first
        vectorstore_service._create_new_index()
        print("Cleared FAISS index.")
        
        # Batch index chunks
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [c.text for c in batch]
            ids = [c.id for c in batch]
            embs = embedding_service.get_embeddings(texts)
            vectorstore_service.add_chunks(ids, embs)
            print(f"Indexed batch {i//batch_size + 1}/{((len(chunks)-1)//batch_size)+1} (size {len(batch)})")
        print("Vectorstore synchronization complete!")
    else:
        print("No chunks found in SQL database to sync.")
finally:
    db.close()
