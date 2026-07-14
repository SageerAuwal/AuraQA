from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.endpoints import auth, upload, documents, chat, study, search
from app.core.context import active_model_var

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the RAG-based AI Document QA System with Multilingual Support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def set_active_model_middleware(request: Request, call_next):
    model_header = request.headers.get("x-ollama-model")
    token = active_model_var.set(model_header)
    try:
        response = await call_next(request)
        return response
    finally:
        active_model_var.reset(token)

# Register Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(study.router, prefix="/api/study", tags=["Study Mode"])
app.include_router(search.router, prefix="/api/search", tags=["Online Search"])

@app.get("/")
def read_root():
    """Service status health check route."""
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "status": "online",
        "supported_languages": settings.SUPPORTED_LANGUAGES
    }
