import os
import sys
from typing import List
from dotenv import load_dotenv

# Resolve app_dir based on frozen status (PyInstaller package vs raw Python development)
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(app_dir, ".env")
load_dotenv(env_path)

# Force Hugging Face offline mode to prevent network-related hangs or update checking delays
os.environ["HF_HUB_OFFLINE"] = "1"

class Settings:
    PROJECT_NAME: str = "AI Document QA System"
    API_V1_STR: str = "/api"
    
    # Folder paths mapped dynamically to keep local SQLite/uploads/index secure in the install path
    APP_DIR: str = app_dir
    UPLOAD_DIR: str = os.path.join(app_dir, "uploads")
    VECTOR_DB_DIR: str = os.path.join(app_dir, "vectorstore")
    
    # Database configuration
    _db_url_env = os.getenv("DATABASE_URL", "")
    if _db_url_env:
        DATABASE_URL: str = _db_url_env
    else:
        _db_path = os.path.join(app_dir, "chatbot.db").replace("\\", "/")
        DATABASE_URL: str = f"sqlite:///{_db_path}"
    
    # JWT configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "9ad0bdc4a48f4f06b72bcf3e4c01e215d389cd8172cd4b1f92e1b891df37a64")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # CORS
    # Splits comma-separated values to support multiple origins if required
    ALLOWED_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()
    ]
    
    # Ollama / Llama 3 Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    
    # Multilingual Whitelist
    SUPPORTED_LANGUAGES: List[str] = ["en", "fr", "ar", "es", "de", "ha"]
    
    # Multilingual Sentence Embedding Model path or name (resolves to bundled folder if frozen)
    @property
    def EMBEDDING_MODEL_PATH(self) -> str:
        if getattr(sys, 'frozen', False):
            path = os.path.join(sys._MEIPASS, "app", "embedding_model")
            if os.path.exists(path):
                return path
        # Fallback to local source path
        local_path = os.path.join(app_dir, "app", "embedding_model")
        if os.path.exists(local_path):
            return local_path
        return "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Cosine Similarity threshold for out-of-scope query filtering
    # Set to 0.40 to allow cross-lingual matches (e.g. Spanish query matching Arabic text)
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.40"))

settings = Settings()
