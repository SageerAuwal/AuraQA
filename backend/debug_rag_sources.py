import sys
import os
sys.path.append(r"c:\Users\HP ProBook\Desktop\ChatBot\backend")

from app.core.database import SessionLocal
from app.services.vectorstore_service import vectorstore_service
from app.services.embedding_service import embedding_service
from app.models.models import DocumentChunk, Document

db = SessionLocal()
try:
    print(f"FAISS index total vectors: {vectorstore_service.index.ntotal}")
    chunks = db.query(DocumentChunk).all()
    print(f"Database total chunks: {len(chunks)}")
    
    if chunks:
        doc = db.query(Document).filter(Document.id == chunks[0].document_id).first()
        print(f"Sample chunk ID: {chunks[0].id}, doc filename: {doc.filename if doc else 'Unknown'}")
        print(f"Sample chunk text: {chunks[0].text[:100]}")
        
        # Search for this sample chunk
        emb = embedding_service.get_embedding(chunks[0].text[:100])
        res = vectorstore_service.search(emb, k=5)
        print(f"Raw FAISS search results for sample chunk text: {res}")
    else:
        print("No chunks in database.")
finally:
    db.close()
