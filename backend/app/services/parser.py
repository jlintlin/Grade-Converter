"""
CSV parsing service.
Owner: Jie Lin, Ph.D. / TLin Investments LLC
"""

import io
import uuid
import time
from typing import Dict, Any, List, Optional

import pandas as pd
from fastapi import HTTPException, UploadFile

from app.core.session import session_storage, cleanup_expired_sessions
from app.models.schemas import AssignmentInfo

# Patterns for read-only columns (these should not be used in grade calculations)
READ_ONLY_PATTERNS = ['Current Score', 'Final Score', 'Unposted', 'Current Points', 'Final Points']

METADATA_COLS = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Root Account', 'Section']


def is_read_only_column(col_name: str) -> bool:
    """Check if a column is read-only (summary/calculated column from Canvas)."""
    return any(pattern in col_name for pattern in READ_ONLY_PATTERNS)


async def parse_canvas_csv(file: UploadFile) -> Dict[str, Any]:
    """Parse the uploaded Canvas CSV, store session data in memory, and return parsed metadata."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Find actual metadata columns present in the file
        metadata_cols_present = [c for c in METADATA_COLS if c in df.columns]

        # Find all non-metadata columns (including read-only for reference)
        all_grade_cols = [col for col in df.columns if col not in METADATA_COLS]

        # Separate assignment columns from read-only columns
        assignment_cols: List[str] = []
        read_only_cols: List[str] = []
        for col in all_grade_cols:
            if is_read_only_column(col):
                read_only_cols.append(col)
            else:
                assignment_cols.append(col)

        # Skip the first two rows (posting info and points possible)
        data_df = df.iloc[2:].copy()

        # Extract points possible from row 1 (index 1)
        points_possible: Dict[str, Optional[float]] = {}
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
            student_dict: Dict[str, Any] = {}
            for col in data_df.columns:
                val = row[col]
                if pd.isna(val) or (isinstance(val, float) and (val != val or val == float('inf') or val == float('-inf'))):
                    student_dict[col] = ''
                else:
                    student_dict[col] = val
            students.append(student_dict)

        # Extract unique sections
        sections: List[str] = []
        if 'Section' in df.columns:
            section_values = data_df['Section'].unique().tolist()
            sections = [s for s in section_values if s and str(s).strip()]

        # Build assignment info (simplified - all assignments are points-based)
        assignment_info: Dict[str, AssignmentInfo] = {}
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

        return {
            "session_id": session_id,
            "headers": list(df.columns),
            "students": students,
            "assignment_columns": assignment_cols,
            "read_only_columns": read_only_cols,
            "assignment_info": assignment_info,
            "metadata_columns": metadata_cols_present,
            "sections": sections,
            "row_count": len(students),
            "original_filename": file.filename or ""
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")
