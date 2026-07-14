from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from app.api.deps import get_db, get_current_user
from app.models.models import User, Document, DocumentSummary, Quiz, FlashcardSet
from app.schemas.study import StudyDashboardOut, DocumentSummaryOut, QuizOut, FlashcardSetOut
from app.services.study_service import study_service

router = APIRouter()

def _format_summary_out(db_sum: DocumentSummary) -> DocumentSummaryOut:
    """Helper to deserialize stored JSON structures into output schema format."""
    return DocumentSummaryOut(
        id=db_sum.id,
        document_id=db_sum.document_id,
        summary_text=db_sum.summary_text,
        key_points=json.loads(db_sum.key_points),
        conclusions=db_sum.conclusions,
        chapters=json.loads(db_sum.chapters)
    )

@router.get("/dashboard/{document_id}", response_model=StudyDashboardOut)
def get_study_dashboard(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all persisted study materials (summaries, quizzes, flashcards)
    for a document, or return empty structures if not generated yet.
    """
    # Verify document ownership
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )

    # 1. Fetch summary
    db_summary = db.query(DocumentSummary).filter(DocumentSummary.document_id == document_id).first()
    summary_out = _format_summary_out(db_summary) if db_summary else None

    # 2. Fetch latest quiz
    db_quiz = db.query(Quiz).filter(Quiz.document_id == document_id, Quiz.user_id == current_user.id).order_by(Quiz.created_at.desc()).first()
    quiz_out = None
    if db_quiz:
        # Formulate options lists back from serialized JSON
        from app.schemas.study import QuizQuestionOut
        questions_out = []
        for q in db_quiz.questions:
            opts = json.loads(q.options) if q.options else None
            questions_out.append(QuizQuestionOut(
                id=q.id,
                question_type=q.question_type,
                question_text=q.question_text,
                options=opts,
                correct_answer=q.correct_answer,
                explanation=q.explanation
            ))
        quiz_out = QuizOut(
            id=db_quiz.id,
            document_id=db_quiz.document_id,
            created_at=db_quiz.created_at,
            questions=questions_out
        )

    # 3. Fetch latest flashcards set
    db_set = db.query(FlashcardSet).filter(FlashcardSet.document_id == document_id, FlashcardSet.user_id == current_user.id).order_by(FlashcardSet.created_at.desc()).first()
    flashcard_out = None
    if db_set:
        from app.schemas.study import FlashcardOut
        cards_out = [
            FlashcardOut(id=c.id, front=c.front, back=c.back)
            for c in db_set.cards
        ]
        flashcard_out = FlashcardSetOut(
            id=db_set.id,
            document_id=db_set.document_id,
            created_at=db_set.created_at,
            cards=cards_out
        )

    return StudyDashboardOut(
        summary=summary_out,
        quiz=quiz_out,
        flashcard_set=flashcard_out
    )

@router.post("/summarize/{document_id}", response_model=DocumentSummaryOut)
async def generate_document_summary(
    document_id: int,
    regenerate: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger the map-reduce automatic summarization and chapter detection pipeline.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )
        
    try:
        if regenerate:
            # Delete existing study materials to allow fresh recalculation
            db.query(DocumentSummary).filter(DocumentSummary.document_id == document_id).delete()
            db.query(Quiz).filter(Quiz.document_id == document_id).delete()
            db.query(FlashcardSet).filter(FlashcardSet.document_id == document_id).delete()
            db.commit()
            
        db_sum = await study_service.generate_document_summary(document_id, db)
        return _format_summary_out(db_sum)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )

@router.post("/quiz/{document_id}", response_model=QuizOut)
async def generate_quiz(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new 9-question quiz grounded in the document summaries.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )
        
    try:
        db_quiz = await study_service.generate_quiz(document_id, current_user.id, db)
        from app.schemas.study import QuizQuestionOut
        return QuizOut(
            id=db_quiz.id,
            document_id=db_quiz.document_id,
            created_at=db_quiz.created_at,
            questions=[
                QuizQuestionOut(
                    id=q.id,
                    question_type=q.question_type,
                    question_text=q.question_text,
                    options=json.loads(q.options) if q.options else None,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation
                )
                for q in db_quiz.questions
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz: {str(e)}"
        )

@router.post("/flashcards/{document_id}", response_model=FlashcardSetOut)
async def generate_flashcards(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new flashcard Q&A set for a document.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )
        
    try:
        db_set = await study_service.generate_flashcards(document_id, current_user.id, db)
        from app.schemas.study import FlashcardOut
        return FlashcardSetOut(
            id=db_set.id,
            document_id=db_set.document_id,
            created_at=db_set.created_at,
            cards=[
                FlashcardOut(id=c.id, front=c.front, back=c.back)
                for c in db_set.cards
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {str(e)}"
        )
