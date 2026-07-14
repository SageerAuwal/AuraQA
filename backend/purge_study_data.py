import sys
import os
from sqlalchemy.orm import Session

# Add the backend directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from app.models.models import DocumentSummary, Quiz, QuizQuestion, FlashcardSet, Flashcard

def purge_data():
    db = SessionLocal()
    try:
        print("Purging study materials database tables...")
        
        # In SQLite, with PRAGMA foreign_keys=ON, deleting Quiz and FlashcardSet will delete Questions and Cards.
        # But we can also truncate/delete them explicitly to be safe.
        num_cards = db.query(Flashcard).delete()
        num_sets = db.query(FlashcardSet).delete()
        num_questions = db.query(QuizQuestion).delete()
        num_quizzes = db.query(Quiz).delete()
        num_summaries = db.query(DocumentSummary).delete()
        
        db.commit()
        print("Purge completed successfully!")
        print(f"Deleted:")
        print(f"  - {num_summaries} Document Summaries")
        print(f"  - {num_quizzes} Quizzes ({num_questions} Questions)")
        print(f"  - {num_sets} Flashcard Sets ({num_cards} Cards)")
        
    except Exception as e:
        db.rollback()
        print(f"Error purging data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    purge_data()
