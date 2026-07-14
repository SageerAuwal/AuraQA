import sys
import os
import asyncio
import time

# Add backend to path
sys.path.append(r"c:\Users\HP ProBook\Desktop\ChatBot\backend")

from app.core.database import SessionLocal
from app.services.rag_service import rag_service
from app.models.models import User, Document, Chat, DocumentChunk

async def main():
    db = SessionLocal()
    try:
        # Find a user who has documents and chunks
        user = db.query(User).join(Document).join(DocumentChunk).first()
        if not user:
            print("Error: No user with uploaded documents/chunks found in database. Cannot run multidoc test.")
            return

        print(f"Using test user: {user.name} (ID: {user.id})")
        user_docs = db.query(Document).filter(Document.user_id == user.id).all()
        print(f"User documents in library: {[d.filename for d in user_docs]}")

        # Create a new General Chat session for this user
        chat = Chat(user_id=user.id, document_id=None)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        print(f"Created test general chat session ID: {chat.id}")

        # Pick a query. We want something that matches content in the documents.
        # Let's inspect a chunk to query something realistic
        sample_chunk = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_([d.id for d in user_docs])).first()
        if sample_chunk:
            # Take first 5 words of the chunk as a query
            query_words = sample_chunk.text.split()[:5]
            query_text = " ".join(query_words)
        else:
            query_text = "What is the summary of the document?"

        print(f"\n--- TEST 1: all_documents=False (Standard General Chat) ---")
        print(f"Query: '{query_text}'")
        res1 = await rag_service.answer_question(
            document_id=None,
            query_text=query_text,
            db=db,
            chat_id=chat.id,
            all_documents=False
        )
        safe_ans1 = res1['answer'].encode('ascii', errors='replace').decode('ascii')
        print(f"Answer: {safe_ans1}")
        print(f"Sources: {res1['sources']}")
        assert len(res1['sources']) == 0, "Test 1 failed: Sources returned when all_documents=False!"
        print("Test 1 Passed: Standard general chat returned no document sources.")

        print(f"\n--- TEST 2: all_documents=True (Library Search Mode) ---")
        print(f"Query: '{query_text}'")
        res2 = await rag_service.answer_question(
            document_id=None,
            query_text=query_text,
            db=db,
            chat_id=chat.id,
            all_documents=True
        )
        safe_ans2 = res2['answer'].encode('ascii', errors='replace').decode('ascii')
        print(f"Answer: {safe_ans2}")
        print(f"Sources: {res2['sources']}")
        if res2['sources']:
            print("Test 2 Passed: Successfully retrieved and cited document sources in General Chat!")
            for src in res2['sources']:
                safe_title = src.get('title', '').encode('ascii', errors='replace').decode('ascii')
                print(f" - Title: {safe_title}, Page: {src.get('page_number')}, Score: {src.get('score')}")
        else:
            print("Test 2 Info: Run completed, but no sources exceeded the similarity threshold.")

        # Clean up test chat
        db.delete(chat)
        db.commit()
        print("\nCleanup completed.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Test run failed: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
