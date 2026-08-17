import datetime
from datetime import date, time, timedelta

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router

from user.api.schemas.dashboard import DashboardSummarySchema, ScorecardDetailSchema
from user.models.attendance import Attendance
from user.models.employee import Employee
from user.models.roles import Department

employee_dashboard_api = Router(tags=["Dashboard"])


def calculate_punctuality(employee):
    today = date.today()
    start_date = today.replace(day=1)

    records = Attendance.objects.filter(
        employee=employee,
        attendance_type="clock_in",
        timestamp__date__range=[start_date, today],
    )

    total_days = records.count()
    on_time_count = 0
    late_count = 0

    for record in records:
        if record.timestamp.time() <= datetime.time(8, 0):
            on_time_count += 1
        else:
            late_count += 1

    punc_score = int((on_time_count / total_days) * 100) if total_days > 0 else 0

    present_dates = set(records.values_list("timestamp__date", flat=True))

    absent_days = 0
    current_day = start_date
    while current_day <= today:
        if current_day.weekday() < 5:
            if current_day not in present_dates:
                absent_days += 1
        current_day += timedelta(days=1)

    return total_days, on_time_count, late_count, absent_days, punc_score


def calculate_rank(employee):
    today = date.today()
    start_date = today.replace(day=1)

    punc_score = int((on_time_count / total_days) * 100) if total_days > 0 else 0
    present_dates = set(records.values_list("timestamp__date", flat=True))

    absent_days = 0
    current_day = start_date
    while current_day <= today:
        if current_day.weekday() < 5:
            if current_day not in present_dates:
                absent_days += 1

        current_day += timedelta(days=1)

    return total_days, on_time_count, late_count, absent_days, punc_score


def calculate_rank(employee):
    today = date.today()
    start_date = today.replace(day=1)

    dept_members = Employee.objects.filter(department=employee.department)
    member_scores = []

    for member in dept_members:
        _, _, _, _, p = calculate_punctuality(member)

        wr_data = member.reports.filter(
            status="approved", created_at__date__range=[start_date, today]
        ).aggregate(Avg("rating"))

        wr_avg = wr_data["rating__avg"] or 0
        score = (p + int((wr_avg / 5) * 100)) / 2
        member_scores.append({"id": member.id, "score": score})

    member_scores.sort(key=lambda x: x["score"], reverse=True)
    rank = (
        next(i for i, item in enumerate(member_scores) if item["id"] == employee.id) + 1
    )

    return rank, dept_members.count()


@employee_dashboard_api.get("/summary", response=DashboardSummarySchema)
def get_dashboard_summary(request):
    employee = get_object_or_404(Employee, user=request.user)
    today = date.today()
    start_date = today.replace(day=1)

    _, _, _, _, punc_score = calculate_punctuality(employee)

    avg_rating = (
        employee.reports.filter(
            status="approved", created_at__date__range=[start_date, today]
        ).aggregate(Avg("rating"))["rating__avg"]
        or 0
    )

    work_report_score = int((avg_rating / 5) * 100)
    overall_score = int((punc_score + work_report_score) / 2)

    rank, total_members = calculate_rank(employee)

    return {
        "full_name": f"{employee.user.first_name} {employee.user.last_name}",
        "job_title": employee.designation,
        "department_name": employee.department.name if employee.department else "N/A",
        "scorecard": {
            "overall_score": overall_score,
            "work_reports_score": work_report_score,
            "punctuality_score": punc_score,
            "rank_text": f"Rank #{rank} of {total_members} in {employee.department.name}",
        },
        "ranking": {"rank": rank, "total_members": total_members},
    }


@employee_dashboard_api.get("/performance-card", response=ScorecardDetailSchema)
def get_performance_card(request):
    employee = get_object_or_404(Employee, user=request.user)
    today = date.today()
    start_date = today.replace(day=1)

    total_days, on_time_days, late_days, absent_days, punc_score = (
        calculate_punctuality(employee)
    )

    monthly_reports = employee.reports.filter(
        created_at__date__range=[start_date, today]
    )
    approved_reports = monthly_reports.filter(status="approved")

    avg_rating = approved_reports.aggregate(Avg("rating"))["rating__avg"] or 0
    work_report_score = int((avg_rating / 5) * 100)

    overall_score = int((punc_score + work_report_score) / 2)
    rank, total_members = calculate_rank(employee)

    return {
        "full_name": f"{employee.user.first_name} {employee.user.last_name}",
        "job_title": employee.designation,
        "department_name": employee.department.name if employee.department else "N/A",
        "overall_score": overall_score,
        "rank_text": f"Rank #{rank} of {total_members} in {employee.department.name}",
        "work_report": {
            "work_report_score": work_report_score,
            "reports_submitted": monthly_reports.count(),
            "approved_reports": approved_reports.count(),
            "average_rating": round(float(avg_rating), 1),
        },
        "punctuality_report": {
            "punctuality_score": punc_score,
            "total_days": total_days,
            "on_time_days": on_time_days,
            "late_days": late_days,
            "absent_days": absent_days,
        },
    }
