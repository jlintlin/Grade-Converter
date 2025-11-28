"""
Canvas Grade Converter - FastAPI Backend
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import io
import os
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI(
    title="Canvas Grade Converter API",
    description="API for converting Canvas gradebook exports",
    version="1.0.0"
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

# Pydantic models
class GradeCategory(BaseModel):
    name: str
    weight: float
    drop_lowest: int = 0
    assignments: List[str] = []

class GradeConfig(BaseModel):
    categories: List[GradeCategory]
    grading_scale: Dict[str, float] = {
        "A": 90.0, "B": 80.0, "C": 70.0, "D": 60.0, "F": 0.0
    }

class ParsedGradeData(BaseModel):
    headers: List[str]
    students: List[Dict[str, Any]]
    assignment_columns: List[str]
    metadata_columns: List[str]
    detected_categories: Dict[str, List[str]]
    row_count: int


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Canvas Grade Converter API"}


@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "healthy"}


@app.post("/api/upload", response_model=ParsedGradeData)
async def upload_grades(file: UploadFile = File(...)):
    """
    Upload and parse a Canvas grade CSV file.
    Returns parsed data including headers, students, and detected categories.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Identify metadata columns vs assignment columns
        metadata_cols = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 
                        'Root Account', 'Section']
        
        # Find actual assignment columns (not read-only score columns)
        assignment_cols = []
        score_cols = []
        
        for col in df.columns:
            if col in metadata_cols:
                continue
            # Skip read-only score summary columns
            if any(x in col for x in ['Current Score', 'Final Score', 'Unposted']):
                score_cols.append(col)
                continue
            assignment_cols.append(col)
        
        # Try to detect categories from assignment names
        detected_categories = detect_categories(assignment_cols)
        
        # Skip the first two rows (posting info and points possible)
        # and convert to list of dicts
        data_df = df.iloc[2:].copy()
        students = data_df.to_dict('records')
        
        return ParsedGradeData(
            headers=list(df.columns),
            students=students,
            assignment_columns=assignment_cols,
            metadata_columns=[c for c in metadata_cols if c in df.columns],
            detected_categories=detected_categories,
            row_count=len(students)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


def detect_categories(columns: List[str]) -> Dict[str, List[str]]:
    """
    Attempt to detect assignment categories from column names.
    Canvas often includes category hints in assignment names.
    """
    categories = {
        "Homework": [],
        "Exam": [],
        "Quiz": [],
        "Activity": [],
        "Project": [],
        "Other": []
    }
    
    for col in columns:
        col_lower = col.lower()
        if 'hw' in col_lower or 'homework' in col_lower:
            categories["Homework"].append(col)
        elif 'exam' in col_lower or 'midterm' in col_lower or 'final' in col_lower:
            categories["Exam"].append(col)
        elif 'quiz' in col_lower:
            categories["Quiz"].append(col)
        elif 'activity' in col_lower or 'participation' in col_lower or 'yellowdig' in col_lower:
            categories["Activity"].append(col)
        elif 'project' in col_lower or 'paper' in col_lower or 'research' in col_lower:
            categories["Project"].append(col)
        else:
            categories["Other"].append(col)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


@app.post("/api/preview")
async def preview_grades(file: UploadFile = File(...), config: str = None):
    """
    Preview calculated grades based on configuration.
    """
    # Placeholder for grade calculation preview
    return {"message": "Preview endpoint - implementation pending"}


@app.post("/api/export")
async def export_grades():
    """
    Export grades to a formatted CSV.
    """
    # Placeholder for export functionality
    return {"message": "Export endpoint - implementation pending"}

