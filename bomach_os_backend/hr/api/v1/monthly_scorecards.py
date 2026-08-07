import logging
from decimal import Decimal
from typing import Optional
from ninja import Router
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import Avg

from hr.models.monthly_scorecard import MonthlyScorecard
from hr.services.scorecard_calculator import (
    generate_scorecard,
    calc_overall_score,
    calc_target_achievement,
    update_rankings,
)
from hr.api.schemas import (
    ScorecardUpdateSchema,
    ScorecardResponseSchema,
    LeaderboardResponseSchema,
    MessageSchema,
)
from hr.utils.auth_client import get_auth_client
from user.utils.perm import require_permission, scope_queryset, check_obj_permission

logger = logging.getLogger(__name__)

router = Router(tags=['Monthly Scorecards'])


@router.get('/leaderboard', response={200: LeaderboardResponseSchema, 400: MessageSchema})
@require_permission("monthly_scorecards", "list")
def get_leaderboard(
    request,
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    if not month or not year:
        return 400, {'detail': 'Month and year are required.'}

    scorecards = MonthlyScorecard.objects.filter(
        month=month, year=year,
    ).order_by('ranking')[:10]  # Limit to top 10 for performance

    # Enrich each scorecard with employee details from gRPC
    entries = []
    for sc in scorecards:
        employee_name = None
        employee_branch = None
        try:
            emp = get_auth_client().get_employee_info(sc.employee_id)
            if emp:
                employee_name = emp.get('full_name')
                employee_branch = emp.get('branch_name')
        except Exception as e:
            logger.warning(f"Failed to fetch employee {sc.employee_id}: {e}")


        entries.append({
            'rank': sc.ranking or 0,
            'employee_id': sc.employee_id,
            'employee_name': employee_name,
            'branch': employee_branch,
            'score': sc.overall_score,
            'award': None,
        })

    total_participants = len(entries)
    avg_score = (
        sum(e['score'] for e in entries) / total_participants
        if total_participants > 0 else Decimal('0.00')
    )

    return 200, {
        'month': month,
        'year': year,
        'entries': entries,
        'avg_score': round(avg_score, 2),
        'total_participants': total_participants,
    }


@router.get('/employee/{employee_id}', response={200: ScorecardResponseSchema, 400: MessageSchema, 404: MessageSchema})
@require_permission("monthly_scorecards", "view", owner_lookup="employee__user")
def get_employee_scorecard(
    request,
    employee_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    if not month or not year:
        return 400, {'detail': 'Month and year are required.'}

    # Check if scorecard already exists, otherwise generate it
    scorecard = MonthlyScorecard.objects.filter(
        employee_id=employee_id,
        month=month,
        year=year,
    ).first()

    if not scorecard:
        scorecard, _ = generate_scorecard(
            employee_id=employee_id,
            month=month,
            year=year,
        )

    # Fetch employee name and level via gRPC
    employee_name = None
    employee_level = None
    try:
        employee = get_auth_client().get_employee_info(employee_id)
        if employee:
            employee_name = employee.get('full_name')
            employee_level = employee.get('position')
    except Exception as e:
        logger.warning(f"Failed to fetch employee details for {employee_id}: {e}")

    # Build response with employee details
    scorecard.employee_name = employee_name
    scorecard.employee_level = employee_level

    return 200, scorecard


@router.put('/{scorecard_id}', response={200: ScorecardResponseSchema, 400: MessageSchema})
@require_permission("monthly_scorecards", "update")
def update_scorecard(request, scorecard_id: int, payload: ScorecardUpdateSchema):
    """Manual override of scorecard scores. Recalculates overall and sets is_auto_generated=False."""
    try:
        scorecard = get_object_or_404(MonthlyScorecard, id=scorecard_id)
        update_data = payload.model_dump(exclude_unset=True)

        for attr, value in update_data.items():
            setattr(scorecard, attr, value)

        # Recalculate overall score from individual metrics
        scores = {
            'attendance': scorecard.attendance_score,
            'task_delivery': scorecard.task_delivery_score,
            'report_accuracy': scorecard.report_accuracy_score,
            'brand_contribution': scorecard.brand_contribution_score,
            'training_progress': scorecard.training_progress_score,
        }
        scorecard.overall_score = calc_overall_score(scores)
        scorecard.target_achievement = calc_target_achievement(
            scorecard.overall_score, scorecard.target_score
        )
        scorecard.is_auto_generated = False

        scorecard.save(skip_validation=True)

        # Update branch rankings
        update_rankings(scorecard.year, scorecard.month)
        scorecard.refresh_from_db()

        return 200, scorecard
    except ValidationError as e:
        return 400, {'detail': e.messages[0] if hasattr(e, 'messages') else str(e)}
