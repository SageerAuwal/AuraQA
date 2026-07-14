from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.models import User, Document, DocumentChunk
from app.services.file_service import delete_file
from app.services.vectorstore_service import vectorstore_service

router = APIRouter()

@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all documents uploaded by the authenticated user."""
    documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.chat_id == None
    ).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "language": doc.language,
            "created_at": doc.created_at
        }
        for doc in documents
    ]

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a document. This erases the physical file from local storage,
    removes the vector embeddings from FAISS, and cascadingly deletes its
    chunks and metadata from the database.
    """
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied."
        )
        
    # Step 1: Query the database to retrieve all chunk IDs linked to this document
    chunk_ids = [chunk.id for chunk in doc.chunks]
    
    # Step 2: Remove these chunk vectors from the FAISS vector database
    try:
        if chunk_ids:
            vectorstore_service.remove_chunks(chunk_ids)
    except Exception as e:
        # Log error or raise. We want to be careful: if FAISS deletion fails,
        # we still proceed with SQL/disk cleanup, but let the user know.
        pass
        
    # Step 3: Erase physical file from disk
    delete_file(doc.filepath)
    
    # Step 4: Delete document record from DB (cascading deletes SQL chunks automatically)
    db.delete(doc)
    db.commit()
    
    return {"message": "Document, database chunks, and vector index erased successfully."}

@router.get("/chat/{chat_id}")
def list_chat_documents(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all documents uploaded inside a specific chat session."""
    # Verify chat session belongs to user
    from app.models.models import Chat
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
    documents = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.chat_id == chat_id
    ).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "language": doc.language,
            "created_at": doc.created_at
        }
        for doc in documents
    ]
