import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.endpoints import auth, upload, documents, chat, study, search
from app.core.context import active_model_var

# Initialize database tables
Base.metadata.create_all(bind=engine)

import sys
import webbrowser
from threading import Timer

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the RAG-based AI Document QA System with Multilingual Support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

def open_browser():
    webbrowser.open("http://127.0.0.1:4000")

@app.on_event("startup")
def startup_event():
    # Only open browser automatically when running as a packaged desktop application
    if getattr(sys, 'frozen', False):
        Timer(1.5, open_browser).start()

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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        # Do not redirect API or documentation routes to index.html
        if path.startswith("api") or path.startswith("docs") or path.startswith("redoc"):
            return await super().get_response(path, scope)
        try:
            return await super().get_response(path, scope)
        except Exception:
            # Fallback to index.html for Next.js SPA client-side routing
            return await super().get_response("index.html", scope)

@app.get("/")
def read_root():
    """Service status health check route."""
    # If static files are mounted, serve index.html directly from the static directory
    static_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "status": "online",
        "supported_languages": settings.SUPPORTED_LANGUAGES
    }

# Mount Next.js static files if they have been compiled into backend/app/static
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    import os
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Start the server synchronously on port 4000 when executed directly
    uvicorn.run(app, host="127.0.0.1", port=4000, log_level="info")
