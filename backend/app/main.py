"""
Canvas Grade Converter - FastAPI Backend
Owner: Jie Lin, Ph.D. / TLin Investments LLC

Privacy-focused design:
- All CSV data is stored in memory only (no disk storage)
- Session-based data management with automatic cleanup
- Data is cleared when session ends or server restarts
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.session import session_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - clears all data on shutdown."""
    yield
    # Clear all session data on shutdown
    session_storage.clear()
    print("All session data cleared on shutdown")


app = FastAPI(
    title="Canvas Grade Converter API",
    description="Privacy-focused API for converting Canvas gradebook exports. All data is stored in memory only.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for local development (supports both HTTP and HTTPS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)
