import os
import sys
import csv

# Ensure the backend directory is in the Python PATH
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.services.extractor_service import extract_text_with_metadata
from app.api.endpoints.upload import detect_document_language

def test_txt_extraction():
    print("Testing TXT extraction...")
    filepath = "test_sample.txt"
    content = "Hello world! This is a simple text file for testing. " * 50  # ~2500 characters
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    try:
        chunks = extract_text_with_metadata(filepath)
        assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
        assert chunks[0]["page_number"] == 1
        assert chunks[1]["page_number"] == 2
        print("[OK] TXT extraction passed.")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

def test_csv_extraction():
    print("Testing CSV extraction...")
    filepath = "test_sample.csv"
    headers = ["Name", "Age", "Role"]
    rows = [
        ["Alice", "30", "Engineer"],
        ["Bob", "25", "Designer"],
        ["Charlie", "35", "Manager"]
    ]
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    try:
        chunks = extract_text_with_metadata(filepath)
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"
        text = chunks[0]["text"]
        assert "Name: Alice" in text
        assert "Age: 30" in text
        assert "Role: Engineer" in text
        assert "Row 1:" in text
        print("[OK] CSV extraction passed.")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

def test_docx_extraction():
    print("Testing DOCX extraction...")
    filepath = "test_sample.docx"
    import docx
    doc = docx.Document()
    # Write paragraph blocks
    for i in range(10):
        doc.add_paragraph(f"Paragraph {i}: This is a paragraph block written to exceed characters. " * 3)
    doc.save(filepath)
    
    try:
        chunks = extract_text_with_metadata(filepath)
        assert len(chunks) >= 1, "Expected at least 1 chunk"
        assert chunks[0]["page_number"] == 1
        print("[OK] DOCX extraction passed.")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

def test_language_detection():
    print("Testing language detection...")
    english_text = "This is a simple document written in English."
    french_text = "Ceci est un document simple écrit en français."
    arabic_text = "هذا مستند بسيط مكتوب باللغة العربية."
    spanish_text = "Este es un documento simple escrito en español."
    german_text = "Dies ist ein einfaches Dokument, das auf Deutsch geschrieben wurde."
    hausa_text = "Wannan takarda ce mai sauki da aka rubuta ta da harshen Hausa."
    
    assert detect_document_language(english_text) == "en", "English detection failed"
    assert detect_document_language(french_text) == "fr", "French detection failed"
    assert detect_document_language(arabic_text) == "ar", "Arabic detection failed"
    assert detect_document_language(spanish_text) == "es", "Spanish detection failed"
    assert detect_document_language(german_text) == "de", "German detection failed"
    
    # Check Hausa detection using our custom helper
    ha_det = detect_document_language(hausa_text)
    assert ha_det == "ha", f"Expected 'ha', but got '{ha_det}'"
    print(f"[OK] Hausa language detected correctly as: {ha_det}")
    
    print("[OK] Language detection passed.")

if __name__ == "__main__":
    print("=== Starting Phase 2 Integration Verification ===")
    try:
        test_txt_extraction()
        test_csv_extraction()
        test_docx_extraction()
        test_language_detection()
        print("=== Verification Successful! ===")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Verification failed: {e}", file=sys.stderr)
        sys.exit(1)
