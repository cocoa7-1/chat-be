import os
import sys

# Ensure project root is in sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import logger
from app.core.middlewares import RequestIDMiddleware

# Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.logs import router as logs_router

settings = get_settings()

# Initialize DB tables immediately
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler: logs startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    init_db()
    logger.info("SQLite Database initialized successfully.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI Web Backend for AI Chatbot Service (AI/SW Basic)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 1. Custom Middlewares
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardized validation error response."""
    errors = exc.errors()
    msg = errors[0].get("msg", "입력값 검증에 실패했습니다.") if errors else "입력값 검증 오류"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": msg, "errors": errors}
    )

# 3. Root & Health Check Endpoint
@app.get("/", tags=["Health"])
def root():
    """Health check and API metadata endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "docs_url": "/docs",
        "api_v1_endpoints": {
            "auth": "/api/v1/auth",
            "chat": "/api/v1/chat",
            "logs": "/api/v1/logs"
        }
    }

# 4. Include API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
