import logging
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router

from hr.api.schemas import (
    EvaluationCreateSchema,
    EvaluationListItemSchema,
    EvaluationResponseSchema,
    EvaluationUpdateSchema,
    MessageSchema,
)
from hr.models.employee_evaluation import EmployeeEvaluation
from hr.models.monthly_scorecard import MonthlyScorecard
from hr.services.scorecard_calculator import generate_scorecard
from hr.utils.auth_client import get_auth_client
from system.authorization import check_obj_permission, require_permission, scope_queryset

logger = logging.getLogger(__name__)

router = Router(tags=["Employee Evaluations"])


def _enrich_evaluation(evaluation):
    """Attach scorecard metrics and employee info to an evaluation instance."""
    # Scorecard metrics
    sc = evaluation.scorecard
    if sc:
        evaluation.attendance_score = sc.attendance_score
        evaluation.task_delivery_score = sc.task_delivery_score
        evaluation.report_accuracy_score = sc.report_accuracy_score
        evaluation.training_progress_score = sc.training_progress_score
        evaluation.brand_contribution_score = sc.brand_contribution_score
        evaluation.overall_score = sc.overall_score
        evaluation.target_score = sc.target_score
        evaluation.target_achievement = sc.target_achievement
        evaluation.ranking = sc.ranking

    # Employee info via gRPC
    try:
        employee = get_auth_client().get_employee_info(evaluation.employee_id)
        if employee:
            evaluation.employee_name = employee.get("full_name")
            evaluation.employee_level = employee.get("position")
    except Exception as e:
        logger.warning(
            f"Failed to fetch employee details for {evaluation.employee_id}: {e}"
        )

    return evaluation


@router.post("/", response={201: EvaluationResponseSchema, 400: MessageSchema})
@require_permission("employee_evaluations", "create")
def create_evaluation(request, payload: EvaluationCreateSchema):
    """Create an evaluation — auto-links or generates the scorecard."""
    try:
        # Find or generate scorecard
        scorecard = MonthlyScorecard.objects.filter(
            employee_id=payload.employee_id,
            month=payload.month,
            year=payload.year,
        ).first()

        if not scorecard:
            try:
                scorecard, _ = generate_scorecard(
                    employee_id=payload.employee_id,
                    month=payload.month,
                    year=payload.year,
                )
            except Exception:
                scorecard = MonthlyScorecard.objects.create(
                    employee_id=payload.employee_id,
                    month=payload.month,
                    year=payload.year,
                )

        evaluation = EmployeeEvaluation.objects.create(
            scorecard=scorecard,
            **payload.model_dump(),
        )

        return 201, _enrich_evaluation(evaluation)
    except ValidationError as e:
        msg = e.messages[0] if hasattr(e, "messages") else str(e)
        return 400, {"detail": msg}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get(
    "/{evaluation_id}", response={200: EvaluationResponseSchema, 404: MessageSchema}
)
@require_permission("employee_evaluations", "view", owner_lookup="employee__user")
def get_evaluation(request, evaluation_id: int):
    """Get a single evaluation with scorecard metrics and employee info."""
    evaluation = get_object_or_404(EmployeeEvaluation, id=evaluation_id)
    check_obj_permission(request, evaluation, owner_field="employee.user")
    return 200, _enrich_evaluation(evaluation)


@router.get("/employee/{employee_id}", response={200: List[EvaluationListItemSchema]})
@require_permission("employee_evaluations", "list", owner_lookup="employee__user")
def list_employee_evaluations(
    request,
    employee_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
):
    """List evaluations for an employee, optionally filtered by month/year."""
    qs = EmployeeEvaluation.objects.filter(employee_id=employee_id)
    qs = scope_queryset(request, qs, owner_field="employee__user")
    if month is not None:
        qs = qs.filter(month=month)
    if year is not None:
        qs = qs.filter(year=year)

    evaluations = list(qs)
    for ev in evaluations:
        sc = ev.scorecard
        ev.overall_score = sc.overall_score if sc else None

    return 200, evaluations


@router.put(
    "/{evaluation_id}", response={200: EvaluationResponseSchema, 400: MessageSchema}
)
@require_permission("employee_evaluations", "update")
def update_evaluation(request, evaluation_id: int, payload: EvaluationUpdateSchema):
    """Update manager comments and recommendation flags."""
    try:
        evaluation = get_object_or_404(EmployeeEvaluation, id=evaluation_id)
        for attr, value in payload.model_dump(exclude_unset=True).items():
            setattr(evaluation, attr, value)
        evaluation.save(skip_validation=True)
        return 200, _enrich_evaluation(evaluation)
    except ValidationError as e:
        msg = e.messages[0] if hasattr(e, "messages") else str(e)
        return 400, {"detail": msg}
