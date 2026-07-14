import os
from typing import List
from dotenv import load_dotenv

# Load environmental variables from the .env file in the backend root directory
# Using absolute path derivation to ensure it resolves regardless of current working directory
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

# Force Hugging Face offline mode to prevent network-related hangs or update checking delays
os.environ["HF_HUB_OFFLINE"] = "1"

class Settings:
    PROJECT_NAME: str = "AI Document QA System"
    API_V1_STR: str = "/api"
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")
    
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
    
    # Multilingual Sentence Embedding Model
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Cosine Similarity threshold for out-of-scope query filtering
    # Set to 0.40 to allow cross-lingual matches (e.g. Spanish query matching Arabic text)
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.40"))

settings = Settings()
