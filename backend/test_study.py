import os
import sys
import asyncio

# Ensure the backend directory is in the Python PATH
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.core.database import SessionLocal, Base, engine
from app.models.models import User, Document, DocumentChunk, DocumentSummary, Quiz, QuizQuestion, FlashcardSet, Flashcard
from app.services.llm_service import llm_service
from app.services.study_service import study_service
from app.services.search_service import search_service

# Mock LLM service responses
async def mock_generate_response(prompt: str, system_prompt: str = "") -> str:
    prompt_lower = prompt.lower()
    system_lower = system_prompt.lower()
    
    if "summarize the following text" in prompt_lower or "academic summarizer" in system_lower:
        return "Title: Segment Test Title\nSummary: This is a test summary of the chapter."
    
    if "comprehensive document summary" in system_lower:
        return (
            "[SUMMARY]\n"
            "This is a test full document summary. It covers general topics.\n"
            "[KEY_POINTS]\n"
            "- Key Concept 1\n"
            "- Key Concept 2\n"
            "[CONCLUSIONS]\n"
            "This is a test conclusion of the document."
        )
        
    if "academic examiner" in system_lower:
        return (
            "[MCQ_START]\n"
            "Q: What is 2 + 2?\n"
            "A) 1\n"
            "B) 2\n"
            "C) 3\n"
            "D) 4\n"
            "Correct: D\n"
            "Explanation: Simple arithmetic.\n"
            "[MCQ_END]\n\n"
            "[TF_START]\n"
            "Q: The sky is blue?\n"
            "Correct: True\n"
            "Explanation: Scattering of light.\n"
            "[TF_END]\n\n"
            "[SHORT_START]\n"
            "Q: Capital of France?\n"
            "Correct: Paris\n"
            "Explanation: Geography.\n"
            "[SHORT_END]"
        )
        
    if "academic study partner" in system_lower:
        return (
            "[CARD_START]\n"
            "Front: Term A\n"
            "Back: Definition A\n"
            "[CARD_END]\n"
            "[CARD_START]\n"
            "Front: Term B\n"
            "Back: Definition B\n"
            "[CARD_END]"
        )
        
    # Search mock responses
    if "web search context" in prompt_lower:
        return "This is a web grounded answer to the search query."
        
    return "Default mock response."

# Override LLM service call
llm_service.generate_response = mock_generate_response

async def run_tests():
    print("Initializing test database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Create a test user
        test_email = "study_test@example.com"
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            db.delete(existing)
            db.commit()
            
        user = User(name="Study Tester", email=test_email, password_hash="hashedpass")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create a test document and chunks
        doc = Document(user_id=user.id, filename="study_guide.txt", filepath="uploads/study_guide.txt", language="en")
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Add 6 chunks to trigger chapter subdivision fallback (groups of 5)
        chunks = []
        for i in range(1, 8):
            chunk = DocumentChunk(
                document_id=doc.id, 
                text=f"This is segment {i} text. It discusses important theories.", 
                page_number=i
            )
            chunks.append(chunk)
        db.add_all(chunks)
        db.commit()
        
        # 1. Test Summarization
        print("Testing Chapter Summarization and Document Summary generation...")
        summary_record = await study_service.generate_document_summary(doc.id, db)
        
        assert summary_record.document_id == doc.id
        assert "test full document summary" in summary_record.summary_text
        assert "Key Concept 1" in summary_record.key_points
        assert "conclusion" in summary_record.conclusions.lower()
        print("[OK] Summarization and chapter analysis passed.")
        
        # 2. Test Quiz Generation
        print("Testing Quiz and QuizQuestion creation...")
        quiz_record = await study_service.generate_quiz(doc.id, user.id, db)
        
        assert quiz_record.document_id == doc.id
        assert len(quiz_record.questions) == 3, f"Expected 3 questions, got {len(quiz_record.questions)}"
        
        # Assert question types exist
        q_types = [q.question_type for q in quiz_record.questions]
        assert "mcq" in q_types
        assert "tf" in q_types
        assert "short" in q_types
        
        mcq_q = next(q for q in quiz_record.questions if q.question_type == "mcq")
        assert mcq_q.correct_answer == "D"
        assert "arithmetic" in mcq_q.explanation
        print("[OK] Quiz and question parser passed.")
        
        # 3. Test Flashcard Generation
        print("Testing Flashcard set creation...")
        flashcard_set = await study_service.generate_flashcards(doc.id, user.id, db)
        
        assert flashcard_set.document_id == doc.id
        assert len(flashcard_set.cards) == 2, f"Expected 2 cards, got {len(flashcard_set.cards)}"
        assert flashcard_set.cards[0].front == "Term A"
        assert flashcard_set.cards[0].back == "Definition A"
        print("[OK] Flashcard set generator passed.")
        
        # 4. Test Search Grounding Flow
        print("Testing Search Grounding Flow...")
        # Mock the search_web method inside search_service to avoid hits to internet
        async def mock_search_web(query: str):
            return {
                "results": [
                    {"title": "Paris info", "url": "https://paris.com", "snippet": "Paris is the capital of France."}
                ],
                "source": "duckduckgo"
            }
        search_service.search_web = mock_search_web
        
        search_res = await search_service.answer_with_web_search("What is the capital of France?")
        assert len(search_res["sources"]) == 1
        assert search_res["sources"][0]["title"] == "Paris info"
        assert search_res["sources"][0]["url"] == "https://paris.com"
        assert "grounded answer" in search_res["answer"]
        print("[OK] Online Search grounding passed.")
        
        # Clean up database records
        print("Cleaning up database test records...")
        db.delete(user) # Cascade deletes doc, chunks, summary, quiz, flashcards
        db.commit()
        print("[OK] Cleanup successful.")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Starting Study and Search Services Verification ===")
    try:
        asyncio.run(run_tests())
        print("=== Verification Successful! ===")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Verification failed: {e}", file=sys.stderr)
        sys.exit(1)
