"""
Canvas Grade Converter - FastAPI Backend

Privacy-focused design:
- All CSV data is stored in memory only (no disk storage)
- Session-based data management with automatic cleanup
- Data is cleared when session ends or server restarts
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import pandas as pd
import io
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager

# In-memory session storage (cleared on restart)
# Structure: { session_id: { 'data': ParsedData, 'created_at': timestamp, 'last_accessed': timestamp } }
session_storage: Dict[str, Dict[str, Any]] = {}

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800


def cleanup_expired_sessions():
    """Remove sessions that have exceeded the timeout period."""
    current_time = time.time()
    expired = [
        sid for sid, session in session_storage.items()
        if current_time - session.get('last_accessed', 0) > SESSION_TIMEOUT
    ]
    for sid in expired:
        del session_storage[sid]
    return len(expired)


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


# Default grading scale (standard scale)
DEFAULT_GRADING_SCALE = {
    "A": 90.0,
    "A-": 87.0,
    "B+": 84.0,
    "B": 80.0,
    "B-": 77.0,
    "C+": 74.0,
    "C": 70.0,
    "C-": 67.0,
    "D+": 64.0,
    "D": 61.0,
    "D-": 57.0,
    "F": 0.0
}


# Pydantic models
class AssignmentInfo(BaseModel):
    name: str
    points_possible: Optional[float] = None
    is_read_only: bool = False  # True for columns like Current Score, Final Score, etc.


class GradeCategory(BaseModel):
    name: str
    weight: float
    drop_lowest: int = 0
    assignments: List[str] = []


class GradeConfig(BaseModel):
    categories: List[GradeCategory]
    grading_scale: Dict[str, float] = DEFAULT_GRADING_SCALE


class ParsedGradeData(BaseModel):
    session_id: str
    headers: List[str]
    students: List[Dict[str, Any]]
    assignment_columns: List[str]
    read_only_columns: List[str] = []
    assignment_info: Dict[str, AssignmentInfo]
    metadata_columns: List[str]
    sections: List[str]
    row_count: int


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Canvas Grade Converter API"}


@app.get("/api/health")
async def health_check():
    """API health check"""
    # Clean up expired sessions periodically
    expired_count = cleanup_expired_sessions()
    return {
        "status": "healthy",
        "active_sessions": len(session_storage),
        "expired_cleaned": expired_count
    }


# Patterns for read-only columns (these should not be used in grade calculations)
READ_ONLY_PATTERNS = ['Current Score', 'Final Score', 'Unposted', 'Current Points', 'Final Points']


def is_read_only_column(col_name: str) -> bool:
    """Check if a column is read-only (summary/calculated column from Canvas)."""
    return any(pattern in col_name for pattern in READ_ONLY_PATTERNS)


@app.post("/api/upload", response_model=ParsedGradeData)
async def upload_grades(file: UploadFile = File(...)):
    """
    Upload and parse a Canvas grade CSV file.

    Privacy features:
    - CSV data is stored in memory only (never written to disk)
    - A unique session ID is generated for this upload
    - Data is automatically cleared after 30 minutes of inactivity
    - Data is cleared when the server restarts

    Returns parsed data including headers, students, and assignment columns.
    Users will define their own categories through the UI.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Define metadata columns
        METADATA_COLS = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Root Account', 'Section']

        # Find actual metadata columns present in the file
        metadata_cols_present = [c for c in METADATA_COLS if c in df.columns]

        # Find all non-metadata columns (including read-only for reference)
        all_grade_cols = [col for col in df.columns if col not in METADATA_COLS]

        # Separate assignment columns from read-only columns
        assignment_cols = []
        read_only_cols = []
        for col in all_grade_cols:
            if is_read_only_column(col):
                read_only_cols.append(col)
            else:
                assignment_cols.append(col)

        # Skip the first two rows (posting info and points possible)
        data_df = df.iloc[2:].copy()

        # Extract points possible from row 1 (index 1)
        points_possible = {}
        if len(df) > 1:
            points_row = df.iloc[1]
            for col in assignment_cols:
                try:
                    val = points_row[col]
                    if pd.notna(val):
                        points_possible[col] = float(str(val).replace(',', ''))
                except (ValueError, TypeError):
                    points_possible[col] = None

        # Replace NaN values for JSON serialization
        data_df = data_df.fillna('')

        # Convert to records with proper handling of non-JSON values
        students = []
        for _, row in data_df.iterrows():
            student_dict = {}
            for col in data_df.columns:
                val = row[col]
                if pd.isna(val) or (isinstance(val, float) and (val != val or val == float('inf') or val == float('-inf'))):
                    student_dict[col] = ''
                else:
                    student_dict[col] = val
            students.append(student_dict)

        # Extract unique sections
        sections = []
        if 'Section' in df.columns:
            section_values = data_df['Section'].unique().tolist()
            sections = [s for s in section_values if s and str(s).strip()]

        # Build assignment info (simplified - all assignments are points-based)
        assignment_info = {}
        for col in assignment_cols:
            pts = points_possible.get(col)
            assignment_info[col] = AssignmentInfo(
                name=col,
                points_possible=pts,
                is_read_only=False
            )

        # Also include read-only columns in assignment_info for reference
        for col in read_only_cols:
            assignment_info[col] = AssignmentInfo(
                name=col,
                points_possible=None,
                is_read_only=True
            )

        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        current_time = time.time()

        # Store data in memory (session-based)
        session_storage[session_id] = {
            'data': {
                'headers': list(df.columns),
                'students': students,
                'assignment_columns': assignment_cols,
                'read_only_columns': read_only_cols,
                'assignment_info': {k: v.dict() for k, v in assignment_info.items()},
                'metadata_columns': metadata_cols_present,
                'sections': sections,
                'points_possible': points_possible,
                'row_count': len(students)
            },
            'created_at': current_time,
            'last_accessed': current_time
        }

        # Clean up expired sessions
        cleanup_expired_sessions()

        return ParsedGradeData(
            session_id=session_id,
            headers=list(df.columns),
            students=students,
            assignment_columns=assignment_cols,
            read_only_columns=read_only_cols,
            assignment_info=assignment_info,
            metadata_columns=metadata_cols_present,
            sections=sections,
            row_count=len(students)
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


@app.get("/api/session/{session_id}")
async def get_session_data(session_id: str):
    """
    Retrieve data for an existing session.
    Updates the last_accessed timestamp to keep session alive.
    """
    if session_id not in session_storage:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Update last accessed time
    session_storage[session_id]['last_accessed'] = time.time()

    return session_storage[session_id]['data']


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """
    Explicitly delete a session and all its data.
    Call this when user clicks "Start Over" or closes the application.
    """
    if session_id in session_storage:
        del session_storage[session_id]
        return {"status": "deleted", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}


class CalculateGradesRequest(BaseModel):
    session_id: str
    categories: List[GradeCategory]
    grading_scale: Dict[str, float] = DEFAULT_GRADING_SCALE


@app.get("/api/grading-scale/default")
async def get_default_grading_scale():
    """
    Get the default grading scale.
    Instructors can use this as a starting point for customization.
    """
    return {
        "scale": DEFAULT_GRADING_SCALE,
        "description": "Standard grading scale"
    }


@app.post("/api/calculate")
async def calculate_grades(request: CalculateGradesRequest):
    """
    Calculate final grades based on user-defined categories and weights.

    This performs the actual grade calculation:
    1. For each category, calculate the weighted average of assigned assignments
    2. Apply drop-lowest rules if specified
    3. Calculate the final weighted grade
    4. Assign letter grades based on the grading scale
    """
    if request.session_id not in session_storage:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = session_storage[request.session_id]
    session['last_accessed'] = time.time()

    students = session['data']['students']
    points_possible = session['data'].get('points_possible', {})

    # Validate that weights sum to 100
    total_weight = sum(cat.weight for cat in request.categories)
    if abs(total_weight - 100) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Category weights must sum to 100% (currently {total_weight}%)"
        )

    calculated_results = []

    for student in students:
        student_result = {
            'Student': student.get('Student', ''),
            'ID': student.get('ID', ''),
            'SIS User ID': student.get('SIS User ID', ''),
            'category_scores': {},
            'final_percentage': 0.0,
            'letter_grade': 'F'
        }

        final_score = 0.0

        for category in request.categories:
            if not category.assignments:
                continue

            # Collect scores for this category
            scores = []
            for assignment in category.assignments:
                try:
                    score_val = student.get(assignment, '')
                    points_max = points_possible.get(assignment)

                    if score_val != '' and points_max and points_max > 0:
                        score = float(score_val)
                        percentage = (score / points_max) * 100
                        scores.append(percentage)
                except (ValueError, TypeError):
                    continue

            # Apply drop lowest
            if category.drop_lowest > 0 and len(scores) > category.drop_lowest:
                scores = sorted(scores, reverse=True)[:-category.drop_lowest]

            # Calculate category average
            if scores:
                category_avg = sum(scores) / len(scores)
            else:
                category_avg = 0.0

            student_result['category_scores'][category.name] = round(category_avg, 2)

            # Add weighted contribution to final score
            final_score += (category_avg * category.weight / 100)

        student_result['final_percentage'] = round(final_score, 2)

        # Assign letter grade
        for grade, min_score in sorted(request.grading_scale.items(),
                                        key=lambda x: x[1], reverse=True):
            if final_score >= min_score:
                student_result['letter_grade'] = grade
                break

        calculated_results.append(student_result)

    return {
        "session_id": request.session_id,
        "results": calculated_results,
        "summary": {
            "total_students": len(calculated_results),
            "grade_distribution": _calculate_distribution(calculated_results)
        }
    }


def _calculate_distribution(results: List[Dict]) -> Dict[str, int]:
    """Calculate grade distribution."""
    distribution = {}
    for result in results:
        grade = result['letter_grade']
        distribution[grade] = distribution.get(grade, 0) + 1
    return distribution


@app.post("/api/export")
async def export_grades(request: CalculateGradesRequest):
    """
    Export calculated grades to a CSV file.
    Returns the CSV as a downloadable file (generated in memory, never stored on disk).
    """
    # First calculate the grades
    if request.session_id not in session_storage:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = session_storage[request.session_id]
    session['last_accessed'] = time.time()

    # Calculate grades (reuse the calculation logic)
    calc_result = await calculate_grades(request)
    results = calc_result['results']

    # Build CSV in memory
    output = io.StringIO()

    # Header row
    category_names = [cat.name for cat in request.categories]
    headers = ['Student', 'ID', 'SIS User ID'] + category_names + ['Final %', 'Letter Grade']
    output.write(','.join(headers) + '\n')

    # Data rows
    for result in results:
        row = [
            f'"{result["Student"]}"',
            str(result['ID']),
            str(result['SIS User ID'])
        ]
        for cat_name in category_names:
            row.append(str(result['category_scores'].get(cat_name, 0)))
        row.append(str(result['final_percentage']))
        row.append(result['letter_grade'])
        output.write(','.join(row) + '\n')

    # Return as downloadable CSV
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"grades_export_{timestamp}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

