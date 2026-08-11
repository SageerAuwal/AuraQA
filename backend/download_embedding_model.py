"""
AuraQA - Embedding Model Downloader
=====================================
Downloads the multilingual sentence embedding model
and saves it locally so the system can run offline.
"""
import os
import sys
from pathlib import Path

# Temporarily enable online mode just for this download
os.environ["HF_HUB_OFFLINE"] = "0"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SAVE_PATH = Path(__file__).resolve().parent / "app" / "embedding_model"

print(f"  Downloading: {MODEL_NAME}")
print(f"  Saving to:   {SAVE_PATH}")
print()

try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    model.save(str(SAVE_PATH))
    print("  Embedding model saved successfully.")
    sys.exit(0)
except ImportError:
    print("  ERROR: sentence-transformers not installed yet.")
    print("  Please run: pip install -r requirements.txt first.")
    sys.exit(1)
except Exception as e:
    print(f"  ERROR downloading model: {e}")
    sys.exit(1)
