from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChapterSummary(BaseModel):
    title: str
    summary: str
    start_page: int
    end_page: int

class DocumentSummaryOut(BaseModel):
    id: int
    document_id: int
    summary_text: str
    key_points: List[str]
    conclusions: str
    chapters: List[ChapterSummary]

    class Config:
        from_attributes = True

class QuizQuestionOut(BaseModel):
    id: int
    question_type: str  # 'mcq', 'tf', 'short'
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None

    class Config:
        from_attributes = True

class QuizOut(BaseModel):
    id: int
    document_id: int
    created_at: datetime
    questions: List[QuizQuestionOut]

    class Config:
        from_attributes = True

class FlashcardOut(BaseModel):
    id: int
    front: str
    back: str

    class Config:
        from_attributes = True

class FlashcardSetOut(BaseModel):
    id: int
    document_id: int
    created_at: datetime
    cards: List[FlashcardOut]

    class Config:
        from_attributes = True

class StudyDashboardOut(BaseModel):
    summary: Optional[DocumentSummaryOut] = None
    quiz: Optional[QuizOut] = None
    flashcard_set: Optional[FlashcardSetOut] = None
