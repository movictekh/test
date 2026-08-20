import calendar
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db.models import Q, Avg

from hr.models.work_report import DailyWorkReport
from hr.models.leave_request import LeaveRequest
from hr.models.disciplinary_case import DisciplinaryCase
from hr.models.monthly_scorecard import MonthlyScorecard

# Metric weights for overall score
WEIGHTS = {
    "attendance": Decimal("0.25"),
    "task_delivery": Decimal("0.25"),
    "report_accuracy": Decimal("0.20"),
    "brand_contribution": Decimal("0.15"),
    "training_progress": Decimal("0.15"),
}

# Severity deductions for disciplinary cases
SEVERITY_DEDUCTIONS = {
    "verbal_warning": Decimal("5"),
    "written_warning": Decimal("10"),
    "final_warning": Decimal("20"),
    "suspension": Decimal("30"),
    "termination": Decimal("50"),
    "demotion": Decimal("25"),
}


def _round(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _weekdays_in_month(year, month):
    """Count the number of weekdays (Mon-Fri) in a given month."""
    num_days = calendar.monthrange(year, month)[1]
    count = 0
    for day in range(1, num_days + 1):
        if date(year, month, day).weekday() < 5:
            count += 1
    return count


def _approved_leave_days(employee_id, year, month):
    """Count approved leave days for an employee in a given month."""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    leaves = LeaveRequest.objects.filter(
        employee_id=employee_id,
        status="approved",
        start_date__lte=month_end,
        end_date__gte=month_start,
    )

    total_days = 0
    for leave in leaves:
        start = max(leave.start_date, month_start)
        end = min(leave.end_date, month_end)
        for day_offset in range((end - start).days + 1):
            d = start + __import__("datetime").timedelta(days=day_offset)
            if d.weekday() < 5:
                total_days += 1
    return total_days


def calc_attendance_score(employee_id, year, month):
    """(non-draft reports / (weekdays - approved leave)) * 100"""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    non_draft_reports = (
        DailyWorkReport.objects.filter(
            employee_id=employee_id,
            day__gte=month_start,
            day__lte=month_end,
        )
        .exclude(status="draft")
        .count()
    )

    weekdays = _weekdays_in_month(year, month)
    approved_leave = _approved_leave_days(employee_id, year, month)
    expected_days = weekdays - approved_leave

    if expected_days <= 0:
        return Decimal("100.00")

    score = (Decimal(non_draft_reports) / Decimal(expected_days)) * Decimal("100")
    return _round(min(score, Decimal("100")))


def calc_task_delivery_score(employee_id, year, month):
    """(approved / total non-draft) * 100"""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    non_draft = DailyWorkReport.objects.filter(
        employee_id=employee_id,
        day__gte=month_start,
        day__lte=month_end,
    ).exclude(status="draft")

    total = non_draft.count()
    if total == 0:
        return Decimal("0.00")

    approved = non_draft.filter(status="approved").count()
    score = (Decimal(approved) / Decimal(total)) * Decimal("100")
    return _round(score)


def calc_report_accuracy_score(employee_id, year, month):
    """(avg rating / 5) * 100"""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    avg_rating = DailyWorkReport.objects.filter(
        employee_id=employee_id,
        day__gte=month_start,
        day__lte=month_end,
        rating__isnull=False,
    ).aggregate(avg=Avg("rating"))["avg"]

    if avg_rating is None:
        return Decimal("0.00")

    score = (Decimal(str(avg_rating)) / Decimal("5")) * Decimal("100")
    return _round(min(score, Decimal("100")))


def calc_brand_contribution_score(employee_id, year, month):
    """100 - severity deductions per case"""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    cases = DisciplinaryCase.objects.filter(
        employee_id=employee_id,
        date_of_violation__gte=month_start,
        date_of_violation__lte=month_end,
    )

    total_deduction = Decimal("0")
    for case in cases:
        deduction = SEVERITY_DEDUCTIONS.get(case.action_type, Decimal("5"))
        total_deduction += deduction

    score = Decimal("100") - total_deduction
    return _round(max(score, Decimal("0")))


def calc_training_progress_score(employee_id, year, month):
    """Placeholder - no employee link in training model."""
    return Decimal("0.00")


def calc_overall_score(scores):
    """Weighted average of the 5 metric scores."""
    overall = (
        scores["attendance"] * WEIGHTS["attendance"]
        + scores["task_delivery"] * WEIGHTS["task_delivery"]
        + scores["report_accuracy"] * WEIGHTS["report_accuracy"]
        + scores["brand_contribution"] * WEIGHTS["brand_contribution"]
        + scores["training_progress"] * WEIGHTS["training_progress"]
    )
    return _round(overall)


def calc_target_achievement(overall_score, target_score):
    """(overall_score / target_score) * 100"""
    if target_score <= 0:
        return Decimal("0.00")
    return _round((overall_score / target_score) * Decimal("100"))


def update_rankings(year, month):
    scorecards = MonthlyScorecard.objects.filter(
        year=year,
        month=month,
    ).order_by("-overall_score")

    for rank, sc in enumerate(scorecards, start=1):
        if sc.ranking != rank:
            MonthlyScorecard.objects.filter(pk=sc.pk).update(ranking=rank)


def generate_scorecard(employee_id, month, year):
    """
    Generate or recalculate a monthly scorecard for an employee.

    Args:
        employee_id: The employee ID
        month: Month (1-12)
        year: Year
        employee_info: Optional dict with employee_name, employee_position, branch_id

    Returns:
        (scorecard, created) tuple
    """
    scores = {
        "attendance": calc_attendance_score(employee_id, year, month),
        "task_delivery": calc_task_delivery_score(employee_id, year, month),
        "report_accuracy": calc_report_accuracy_score(employee_id, year, month),
        "brand_contribution": calc_brand_contribution_score(employee_id, year, month),
        "training_progress": calc_training_progress_score(employee_id, year, month),
    }

    overall = calc_overall_score(scores)
    target_score = Decimal("75.00")

    scorecard, created = MonthlyScorecard.objects.get_or_create(
        employee_id=employee_id,
        month=month,
        year=year,
        defaults={"target_score": target_score},
    )

    # Keep existing target_score if updating
    if not created:
        target_score = scorecard.target_score

    scorecard.attendance_score = scores["attendance"]
    scorecard.task_delivery_score = scores["task_delivery"]
    scorecard.report_accuracy_score = scores["report_accuracy"]
    scorecard.brand_contribution_score = scores["brand_contribution"]
    scorecard.training_progress_score = scores["training_progress"]
    scorecard.overall_score = overall
    scorecard.target_achievement = calc_target_achievement(overall, target_score)
    scorecard.is_auto_generated = True

    scorecard.save(skip_validation=True)

    # Update branch rankings
    update_rankings(year, month)
    scorecard.refresh_from_db()

    return scorecard, created
