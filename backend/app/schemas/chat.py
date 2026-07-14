from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChatSessionCreate(BaseModel):
    document_id: Optional[int] = None

class ChatSessionOut(BaseModel):
    id: int
    document_id: Optional[int]
    user_id: int

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    chat_id: int
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

class ChatMessageRequest(BaseModel):
    chat_id: int
    content: str
    all_documents: Optional[bool] = False

class SourceDetail(BaseModel):
    page_number: int
    score: float
    title: Optional[str] = None

class ChatMessageResponse(BaseModel):
    answer: str
    sources: List[SourceDetail]
    max_score: float
    out_of_scope: bool
