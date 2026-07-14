from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.models import User, Document, Chat, Message
from app.schemas.chat import ChatSessionCreate, ChatSessionOut, ChatMessageRequest, ChatMessageResponse, MessageOut
from app.services.rag_service import rag_service

router = APIRouter()

@router.post("/session", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session linked to a specific uploaded document or a general session."""
    if session_in.document_id is not None:
        # Verify document exists and belongs to the active user
        doc = db.query(Document).filter(
            Document.id == session_in.document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied."
            )
        
    # Create the chat session record
    db_chat = Chat(
        document_id=session_in.document_id,
        user_id=current_user.id
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

@router.get("/sessions", response_model=List[ChatSessionOut])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all chat sessions created by the active user."""
    return db.query(Chat).filter(Chat.user_id == current_user.id).all()

@router.get("/history/{chat_id}", response_model=List[MessageOut])
def get_chat_history(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve chronological message history for a specific chat session."""
    # Verify session belongs to the user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
        
    # Fetch messages ordered by timestamp ascending
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp.asc()).all()
    return messages

@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    msg_request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message. Generates the response using the RAG pipeline
    and registers both user and assistant messages in the database.
    """
    # 1. Verify chat session belongs to the user
    chat = db.query(Chat).filter(
        Chat.id == msg_request.chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
        
    # 2. Persist the User query message
    user_msg = Message(
        chat_id=msg_request.chat_id,
        role="user",
        content=msg_request.content
    )
    db.add(user_msg)
    db.commit()
    
    # 3. Call the async RAG QA pipeline
    try:
        rag_result = await rag_service.answer_question(
            document_id=chat.document_id,
            query_text=msg_request.content,
            db=db,
            chat_id=chat.id,
            all_documents=msg_request.all_documents
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during search execution: {str(e)}"
        )
        
    # 4. Persist the Assistant response message
    assistant_msg = Message(
        chat_id=msg_request.chat_id,
        role="assistant",
        content=rag_result["answer"]
    )
    db.add(assistant_msg)
    db.commit()
    
    return ChatMessageResponse(
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        max_score=rag_result["max_score"],
        out_of_scope=rag_result["out_of_scope"]
    )

@router.post("/message/stream")
async def send_chat_message_stream(
    msg_request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message and stream response tokens using Server-Sent Events (SSE).
    Persists user query message immediately, then collects and persists the 
    completed assistant response after streaming completes.
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    
    # 1. Verify chat session belongs to the user
    chat = db.query(Chat).filter(
        Chat.id == msg_request.chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
        
    # 2. Persist the User query message
    user_msg = Message(
        chat_id=msg_request.chat_id,
        role="user",
        content=msg_request.content
    )
    db.add(user_msg)
    db.commit()
    
    # 3. Create generator to yield SSE chunks and capture final response
    async def event_generator():
        collected_tokens = []
        try:
            generator = rag_service.answer_question_stream(
                document_id=chat.document_id,
                query_text=msg_request.content,
                db=db,
                chat_id=chat.id,
                all_documents=msg_request.all_documents
            )
            async for token in generator:
                collected_tokens.append(token)
                # Yield in SSE format
                yield f"data: {token}\n\n"
                await asyncio.sleep(0.002)
                
            # After streaming finishes, save the full response to database
            final_answer = "".join(collected_tokens).strip()
            if final_answer:
                assistant_msg = Message(
                    chat_id=msg_request.chat_id,
                    role="assistant",
                    content=final_answer
                )
                db.add(assistant_msg)
                db.commit()
        except Exception as e:
            yield f"data: [Error: {str(e)}]\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.delete("/session/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific chat session and all its messages."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or access denied."
        )
        
    db.delete(chat)
    db.commit()
    return None
