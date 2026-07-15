import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings

UPLOAD_DIR = settings.UPLOAD_DIR

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}

# Accepted MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
    "application/octet-stream",  # Fallback for plain files
}

def init_upload_dir():
    """Ensure the uploads folder exists."""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def validate_file(file: UploadFile):
    """Verify that file extension matches whitelisted formats."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no name"
        )
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {ext}. Only PDF, DOCX, TXT, and CSV are allowed."
        )

def save_file(file: UploadFile) -> str:
    """
    Save the uploaded file to disk with a secure, unique filename.
    Returns the absolute path to the stored file.
    """
    validate_file(file)
    init_upload_dir()
    
    # Extract extension and generate unique secure name
    ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        # Reset file cursor to read from beginning
        file.file.seek(0)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
        
    return filepath

def delete_file(filepath: str):
    """Delete the physical file from the local storage disk."""
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            # Silently log/ignore to prevent blocking DB operations
            pass
