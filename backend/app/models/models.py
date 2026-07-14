import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    language = Column(String(10), nullable=True)  # Stores language code ('en', 'fr', 'ar', 'es', 'de', 'ha')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chats = relationship("Chat", back_populates="document", foreign_keys="[Chat.document_id]", cascade="all, delete-orphan")
    chat = relationship("Chat", back_populates="in_chat_documents", foreign_keys="[Document.chat_id]")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    summary = relationship("DocumentSummary", back_populates="document", uselist=False, cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="document", cascade="all, delete-orphan")
    flashcard_sets = relationship("FlashcardSet", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)  # Page number for PDF/DOCX, row number for CSV
    
    # Relationships
    document = relationship("Document", back_populates="chunks")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="chats", foreign_keys="[Chat.document_id]")
    in_chat_documents = relationship("Document", back_populates="chat", foreign_keys="[Document.chat_id]", cascade="all, delete-orphan")
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")


class DocumentSummary(Base):
    __tablename__ = "document_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    key_points = Column(Text, nullable=False)  # JSON list
    conclusions = Column(Text, nullable=False)
    chapters = Column(Text, nullable=False)  # JSON representation of chapters list with text summaries
    
    # Relationships
    document = relationship("Document", back_populates="summary")


class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="quizzes")
    user = relationship("User")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_type = Column(String(20), nullable=False)  # 'mcq', 'tf', 'short'
    question_text = Column(Text, nullable=False)
    options = Column(Text, nullable=True)  # JSON array for MCQ options
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="questions")


class FlashcardSet(Base):
    __tablename__ = "flashcard_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="flashcard_sets")
    user = relationship("User")
    cards = relationship("Flashcard", back_populates="set", cascade="all, delete-orphan")


class Flashcard(Base):
    __tablename__ = "flashcards"
    
    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(Integer, ForeignKey("flashcard_sets.id", ondelete="CASCADE"), nullable=False)
    front = Column(Text, nullable=False)  # Question
    back = Column(Text, nullable=False)  # Answer
    
    # Relationships
    set = relationship("FlashcardSet", back_populates="cards")

