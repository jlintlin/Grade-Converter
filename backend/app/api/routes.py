"""
API routes for Canvas Grade Converter.
Owner: Jie Lin, Ph.D. / TLin Investments LLC
"""

from fastapi import APIRouter, UploadFile
from fastapi import HTTPException

from app.core.session import session_storage, cleanup_expired_sessions, touch_session
from app.models.schemas import (
    ParsedGradeData,
    CalculateGradesRequest,
    DEFAULT_GRADING_SCALE,
)
from app.services.parser import parse_canvas_csv
from app.services.grading import calculate_grades_logic, export_grades_logic

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Canvas Grade Converter API"}


@router.get("/api/health")
async def health_check():
    """API health check"""
    expired_count = cleanup_expired_sessions()
    return {
        "status": "healthy",
        "active_sessions": len(session_storage),
        "expired_cleaned": expired_count
    }


@router.post("/api/upload", response_model=ParsedGradeData)
async def upload_grades(file: UploadFile):
    """Upload and parse a Canvas grade CSV file."""
    return await parse_canvas_csv(file)


@router.get("/api/session/{session_id}")
async def get_session_data(session_id: str):
    """
    Retrieve data for an existing session.
    Updates the last_accessed timestamp to keep session alive.
    """
    if session_id not in session_storage:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    touch_session(session_id)
    return session_storage[session_id]['data']


@router.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Explicitly delete a session and all its data.
    Call this when user clicks "Start Over" or closes the application.
    """
    if session_id in session_storage:
        del session_storage[session_id]
        return {"status": "deleted", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}


@router.get("/api/grading-scale/default")
async def get_default_grading_scale():
    """
    Get the default grading scale.
    Instructors can use this as a starting point for customization.
    """
    return {
        "scale": DEFAULT_GRADING_SCALE,
        "description": "Standard grading scale"
    }


@router.post("/api/calculate")
async def calculate_grades(request: CalculateGradesRequest):
    """
    Calculate final grades based on user-defined categories and weights.
    """
    return calculate_grades_logic(request)


@router.post("/api/export")
async def export_grades(request: CalculateGradesRequest):
    """
    Export calculated grades to a CSV file.
    Returns the CSV as a downloadable file (generated in memory, never stored on disk).
    """
    return export_grades_logic(request)
