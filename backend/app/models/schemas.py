"""
Pydantic schemas and defaults.
Owner: Jie Lin, Ph.D. / TLin Investments LLC
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

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
    "F": 0.0,
}


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
    original_filename: str = ""
    assignment_info: Dict[str, AssignmentInfo]
    metadata_columns: List[str]
    sections: List[str]
    row_count: int


class ReplacementRule(BaseModel):
    """A replacement rule: one assignment can replace the lowest of target assignments"""
    replacer: str  # The assignment that can replace others
    targets: List[str]  # The assignments that can be replaced


class CalculateGradesRequest(BaseModel):
    session_id: str
    categories: List[GradeCategory]
    grading_scale: Dict[str, float] = DEFAULT_GRADING_SCALE
    replacement_rules: Dict[str, List[str]] = {}  # Maps replacer assignment to list of target assignments
