import os
import sys
import asyncio

# Ensure the backend directory is in the Python PATH
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.core.database import SessionLocal, Base, engine
from app.models.models import User, Document, DocumentChunk, Chat, Message
from app.services.embedding_service import embedding_service
from app.services.vectorstore_service import vectorstore_service
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

# Mock local LLM text generation
async def mock_generate_response(prompt: str, system_prompt: str = "", **kwargs) -> str:
    prompt_lower = prompt.lower()
    if "felines" in prompt_lower or "cat" in prompt_lower:
        return "The domestic cat is the user's favorite animal."
    if "context:" in prompt_lower:
        return "NOT_FOUND"
    return "This is a mock response from the LLM."

# Override the service method with our mock
llm_service.generate_response = mock_generate_response

async def run_tests():
    print("Initializing test database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    # Reset vector store to testing state
    vectorstore_service._create_new_index()
    
    try:
        # 1. Create a test user
        test_email = "rag_test@example.com"
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            db.delete(existing)
            db.commit()
            
        user = User(name="RAG Tester", email=test_email, password_hash="hashedpass")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 2. Create two separate test documents (Document A and Document B)
        doc_a = Document(user_id=user.id, filename="pets.txt", filepath="uploads/pets.txt", language="en")
        doc_b = Document(user_id=user.id, filename="cooking.txt", filepath="uploads/cooking.txt", language="en")
        db.add_all([doc_a, doc_b])
        db.commit()
        db.refresh(doc_a)
        db.refresh(doc_b)
        
        # 3. Create document chunks for both
        chunk_a = DocumentChunk(document_id=doc_a.id, text="My favorite animal is the domestic cat. Cats are felines.", page_number=1)
        chunk_b = DocumentChunk(document_id=doc_b.id, text="To bake a cake, you need flour, sugar, eggs, and butter.", page_number=1)
        db.add_all([chunk_a, chunk_b])
        db.commit()
        db.refresh(chunk_a)
        db.refresh(chunk_b)
        
        # 4. Generate embeddings and add to the FAISS index
        emb_a = embedding_service.get_embedding(chunk_a.text)
        emb_b = embedding_service.get_embedding(chunk_b.text)
        
        vectorstore_service.add_chunks([chunk_a.id, chunk_b.id], [emb_a, emb_b])
        
        # 5. Create a chat session linked specifically to Document A
        chat = Chat(document_id=doc_a.id, user_id=user.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        # 6. Test RAG Search: In-Scope query
        print("Testing RAG Search (In-Scope)...")
        res = await rag_service.answer_question(document_id=doc_a.id, query_text="Tell me about felines and cat", db=db)
        
        assert not res["out_of_scope"], "Expected query to be classified as in-scope"
        assert len(res["sources"]) == 1, f"Expected 1 source chunk, got {len(res['sources'])}"
        assert res["sources"][0]["page_number"] == 1, "Expected page number 1"
        assert "cat" in res["answer"].lower(), "Expected cat in LLM generated answer"
        print(f"[OK] In-scope search successful. Answer: {res['answer']}")
        
        # 7. Test RAG Search: Out-of-Scope query (similarity threshold check)
        print("Testing RAG Search (Out-of-Scope threshold check)...")
        res_out = await rag_service.answer_question(document_id=doc_a.id, query_text="What is the capital of France?", db=db)
        
        assert res_out["out_of_scope"], "Expected query to be classified as out-of-scope"
        assert "not available in the uploaded document" in res_out["answer"], "Expected fallback message"
        assert len(res_out["sources"]) == 0, "Expected 0 sources for out-of-scope response"
        print(f"[OK] Out-of-scope search successfully blocked. Answer: {res_out['answer']}")
        
        # 8. Test Document Separation (querying cake on Document A / pets session)
        print("Testing Document Context Separation...")
        res_sep = await rag_service.answer_question(document_id=doc_a.id, query_text="What ingredients do I need for cake?", db=db)
        
        assert res_sep["out_of_scope"], "Expected query to be blocked as out-of-scope due to context isolation"
        print(f"[OK] Document context separation passed. Answer: {res_sep['answer']}")
        
        # 9. Clean up test records
        print("Cleaning up database test records...")
        db.delete(user)  # Cascade delete handles docs, chunks, and chats
        db.commit()
        
        # Clean FAISS index
        vectorstore_service.remove_chunks([chunk_a.id, chunk_b.id])
        print("[OK] Database and vector cleanup passed.")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Starting Phase 4 Integration Verification ===")
    try:
        asyncio.run(run_tests())
        print("=== Verification Successful! ===")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Verification failed: {e}", file=sys.stderr)
        sys.exit(1)
