import os
import csv
from typing import List, Dict, Any
from fastapi import HTTPException, status
from pypdf import PdfReader
import docx

def extract_text_from_pdf(filepath: str) -> List[Dict[str, Any]]:
    """Extract text page-by-page from a PDF file, segmenting into smaller chunks if necessary."""
    chunks = []
    chunk_size = 1000
    overlap = 150
    step = chunk_size - overlap
    try:
        with open(filepath, "rb") as f:
            reader = PdfReader(f)
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    text_content = text.strip()
                    if len(text_content) <= chunk_size:
                        chunks.append({
                            "text": text_content,
                            "page_number": page_idx + 1
                        })
                    else:
                        for i in range(0, len(text_content), step):
                            chunk_text = text_content[i:i+chunk_size].strip()
                            if chunk_text:
                                chunks.append({
                                    "text": chunk_text,
                                    "page_number": page_idx + 1
                                })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )
    return chunks

def extract_text_from_docx(filepath: str) -> List[Dict[str, Any]]:
    """Extract paragraphs from a DOCX file and group them into logical page chunks with overlap."""
    chunks = []
    try:
        try:
            with open(filepath, "rb") as f:
                doc = docx.Document(f)
                paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        except Exception as docx_err:
            print(f"[DOCX WARNING] python-docx parsing failed: {str(docx_err)}. Attempting zip-based manual XML extraction...")
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(filepath) as z:
                doc_xml = z.read("word/document.xml")
                root = ET.fromstring(doc_xml)
                paragraphs = []
                for elem in root.iter():
                    if elem.tag.endswith('}p'):
                        p_text = "".join([child.text for child in elem.iter() if child.tag.endswith('}t') and child.text])
                        if p_text.strip():
                            paragraphs.append(p_text.strip())
                            
        content = "\n".join(paragraphs)
        if not content:
            return chunks
            
        chunk_size = 1000
        overlap = 150
        page_num = 1
        step = chunk_size - overlap
        
        for i in range(0, len(content), step):
            chunk_text = content[i:i+chunk_size].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "page_number": page_num
                })
                page_num += 1
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from DOCX: {str(e)}"
        )
    return chunks

def extract_text_from_txt(filepath: str) -> List[Dict[str, Any]]:
    """Read a TXT file and segment it into chunks of 1000 characters with 150-character overlap."""
    chunks = []
    try:
        # Using utf-8 with ignore error handler to prevent failures on mixed encoding files
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()
            
        if not content:
            return chunks
            
        chunk_size = 1000
        overlap = 150
        page_num = 1
        step = chunk_size - overlap
        for i in range(0, len(content), step):
            chunk_text = content[i:i+chunk_size].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "page_number": page_num
                })
                page_num += 1
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from TXT: {str(e)}"
        )
    return chunks

def extract_text_from_csv(filepath: str) -> List[Dict[str, Any]]:
    """
    Read a CSV file row-by-row, formatting columns as 'Header: Value' pairs,
    and group them into sets of 15 rows to preserve tabular context.
    """
    chunks = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                return chunks
                
            current_rows = []
            row_idx = 1
            page_num = 1
            
            for row in reader:
                if not any(row):  # Skip entirely empty rows
                    continue
                # Map header name to cell value for clean LLM parsing
                row_str = ", ".join([
                    f"{headers[i].strip() if i < len(headers) else f'Col_{i+1}'}: {row[i].strip()}"
                    for i in range(min(len(headers), len(row)))
                ])
                current_rows.append(f"Row {row_idx}: {row_str}")
                row_idx += 1
                
                # Chunk size of 15 rows
                if len(current_rows) >= 15:
                    chunks.append({
                        "text": "\n".join(current_rows),
                        "page_number": page_num
                    })
                    current_rows = []
                    page_num += 1
                    
            # Capture trailing rows
            if current_rows:
                chunks.append({
                    "text": "\n".join(current_rows),
                    "page_number": page_num
                })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from CSV: {str(e)}"
        )
    return chunks

def extract_text_with_metadata(filepath: str) -> List[Dict[str, Any]]:
    """
    Dispatcher function that selects the correct parser based on file extension.
    Returns a list of dicts with keys 'text' and 'page_number'.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext == ".docx":
        return extract_text_from_docx(filepath)
    elif ext == ".txt":
        return extract_text_from_txt(filepath)
    elif ext == ".csv":
        return extract_text_from_csv(filepath)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type for extraction: {ext}"
        )
