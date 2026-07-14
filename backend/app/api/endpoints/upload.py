from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional
from langdetect import detect
from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.models import User, Document, DocumentChunk
from app.services.file_service import save_file, delete_file
from app.services.extractor_service import extract_text_with_metadata
from app.services.embedding_service import embedding_service
from app.services.vectorstore_service import vectorstore_service

router = APIRouter()

def detect_document_language(text: str) -> str:
    """
    Detects the language of the document.
    Includes fallback heuristics for Hausa, which is sometimes misidentified
    by langdetect as Indonesian ('id') or Tagalog ('tl') for shorter texts.
    """
    if not text.strip():
        return "en"
        
    try:
        detected_lang = detect(text)
        
        # Heuristics check for Hausa keywords if classifier returns ID/TL/SO
        if detected_lang in {"id", "tl", "so"}:
            hausa_keywords = {
                "wannan", "harshen", "sauki", "aka", "rubuta", "kuma", 
                "haka", "domin", "hanya", "sarki", "gari", "baba", "rana"
            }
            words = set(text.lower().split())
            if len(words.intersection(hausa_keywords)) >= 2:
                return "ha"
                
        return detected_lang
    except Exception:
        return "en"

@router.post("/file", status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    chat_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document, extract text, detect language, save metadata/chunks to SQL,
    generate semantic vector embeddings, and store them in the FAISS index.
    """
    # Step 1: Save the file to disk using file_service (verifies extension)
    filepath = save_file(file)
    db_doc = None
    
    try:
        # Step 2: Extract text and metadata (page numbers) using extractor_service
        chunks = extract_text_with_metadata(filepath)
        if not chunks:
            delete_file(filepath)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file contains no readable text."
            )
            
        # Step 3: Run language detection on a sample of the text (up to the first 3 chunks)
        sample_text = " ".join([c["text"] for c in chunks[:3]])
        detected_lang = detect_document_language(sample_text)
                
        # Step 4: Validate that detected language is within our 6-language whitelist
        if detected_lang not in settings.SUPPORTED_LANGUAGES:
            delete_file(filepath)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported language detected: '{detected_lang}'. "
                    f"Only English (en), French (fr), Arabic (ar), Spanish (es), "
                    f"German (de), and Hausa (ha) are supported."
                )
            )
            
        # Verify chat session if provided
        if chat_id is not None:
            from app.models.models import Chat
            chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found or access denied."
                )

        # Step 5: Save Document record in the SQL database
        db_doc = Document(
            user_id=current_user.id,
            filename=file.filename,
            filepath=filepath,
            language=detected_lang,
            chat_id=chat_id
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        # Step 6: Save DocumentChunk records in the SQL database
        db_chunks = [
            DocumentChunk(
                document_id=db_doc.id,
                text=chunk["text"],
                page_number=chunk["page_number"]
            )
            for chunk in chunks
        ]
        db.add_all(db_chunks)
        db.commit()
        
        # Step 7: Compute semantic embeddings and add them to FAISS Vector store
        try:
            texts = [chunk.text for chunk in db_chunks]
            chunk_ids = [chunk.id for chunk in db_chunks]
            
            # Generate vectors
            embeddings = embedding_service.get_embeddings(texts)
            
            # Insert into FAISS Index using database generated chunk IDs
            vectorstore_service.add_chunks(chunk_ids, embeddings)
        except Exception as embedding_err:
            # Transactional integrity: If embedding or vector indexing fails,
            # clean up DB records and raise exception so outer handler runs file delete
            if db_doc:
                db.delete(db_doc)
                db.commit()
            raise embedding_err
        
        return {
            "document_id": db_doc.id,
            "filename": db_doc.filename,
            "language": db_doc.language,
            "chunks_count": len(db_chunks),
            "message": "File uploaded, parsed, and vectorized successfully."
        }
        
    except HTTPException:
        # Re-raise planned HTTPExceptions directly
        raise
    except Exception as e:
        # Cleanup saved file on server disk to prevent orphaned files
        delete_file(filepath)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the file: {str(e)}"
        )
