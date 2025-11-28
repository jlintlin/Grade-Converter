"""
Grading and export service.
Owner: Jie Lin, Ph.D. / TLin Investments LLC
"""

import io
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.core.session import session_storage, touch_session
from app.models.schemas import CalculateGradesRequest


def _get_assignment_percentage(student: Dict, assignment: str, points_possible: Dict) -> Optional[float]:
    """Get the percentage score for an assignment, or None if not available."""
    try:
        score_val = student.get(assignment, '')
        points_max = points_possible.get(assignment)
        if score_val != '' and points_max and points_max > 0:
            score = float(score_val)
            return (score / points_max) * 100
    except (ValueError, TypeError):
        pass
    return None


def _apply_replacement_rules(
    student: Dict,
    points_possible: Dict,
    replacement_rules: Dict[str, List[str]],
    category_assignments: Dict[str, List[str]]
) -> Dict:
    """
    Apply replacement rules for a student.
    Returns a dict with:
      - 'replaced_scores': dict mapping target assignment to new score
      - 'replacement_info': list of replacement details for display
    """
    replaced_scores = {}
    replacement_info = []

    for replacer, targets in replacement_rules.items():
        replacer_score = _get_assignment_percentage(student, replacer, points_possible)
        if replacer_score is None:
            continue

        # Find the lowest score among targets that the replacer can improve
        lowest_target = None
        lowest_score = None

        for target in targets:
            target_score = _get_assignment_percentage(student, target, points_possible)
            if target_score is not None and target_score < replacer_score:
                if lowest_score is None or target_score < lowest_score:
                    lowest_score = target_score
                    lowest_target = target

        # Apply replacement if we found a target to replace
        if lowest_target is not None:
            replaced_scores[lowest_target] = replacer_score
            # Find which category the target belongs to
            target_category = None
            for cat_name, assignments in category_assignments.items():
                if lowest_target in assignments:
                    target_category = cat_name
                    break

            replacement_info.append({
                'replacer': replacer,
                'replaced': lowest_target,
                'original_score': round(lowest_score, 2),
                'new_score': round(replacer_score, 2),
                'improvement': round(replacer_score - lowest_score, 2),
                'category': target_category
            })

    return {
        'replaced_scores': replaced_scores,
        'replacement_info': replacement_info
    }


def _calculate_distribution(results: List[Dict]) -> Dict[str, int]:
    """Calculate grade distribution."""
    distribution = {}
    for result in results:
        grade = result['letter_grade']
        distribution[grade] = distribution.get(grade, 0) + 1
    return distribution


def calculate_grades_logic(request: CalculateGradesRequest) -> Dict[str, Any]:
    """Pure calculation logic separated from FastAPI route for reuse."""
    if request.session_id not in session_storage:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    session = session_storage[request.session_id]
    touch_session(request.session_id)

    students = session['data']['students']
    points_possible = session['data'].get('points_possible', {})

    # Validate that weights sum to 100
    total_weight = sum(cat.weight for cat in request.categories)
    if abs(total_weight - 100) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Category weights must sum to 100% (currently {total_weight}%)"
        )

    # Build category assignments map for replacement tracking
    category_assignments = {cat.name: cat.assignments for cat in request.categories}

    calculated_results = []

    for student in students:
        student_result = {
            'Student': student.get('Student', ''),
            'ID': student.get('ID', ''),
            'SIS User ID': student.get('SIS User ID', ''),
            'category_scores': {},
            'final_percentage': 0.0,
            'letter_grade': 'F',
            'replacement_info': None
        }

        # Apply replacement rules if any
        replaced_scores = {}
        if request.replacement_rules:
            replacement_result = _apply_replacement_rules(
                student, points_possible, request.replacement_rules, category_assignments
            )
            replaced_scores = replacement_result['replaced_scores']
            if replacement_result['replacement_info']:
                student_result['replacement_info'] = replacement_result['replacement_info']

        final_score = 0.0

        for category in request.categories:
            if not category.assignments:
                continue

            # Collect scores for this category (with replacements applied)
            scores = []
            for assignment in category.assignments:
                # Check if this assignment was replaced
                if assignment in replaced_scores:
                    scores.append(replaced_scores[assignment])
                else:
                    percentage = _get_assignment_percentage(student, assignment, points_possible)
                    if percentage is not None:
                        scores.append(percentage)

            # Apply drop lowest
            if category.drop_lowest > 0 and len(scores) > category.drop_lowest:
                scores = sorted(scores, reverse=True)[:-category.drop_lowest]

            # Calculate category average
            category_avg = sum(scores) / len(scores) if scores else 0.0
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


def export_grades_logic(request: CalculateGradesRequest) -> StreamingResponse:
    """Generate CSV export from calculated grades."""
    calc_result = calculate_grades_logic(request)
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
