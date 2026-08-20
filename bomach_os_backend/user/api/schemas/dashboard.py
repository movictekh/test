from ninja import Schema
from typing import List, Optional

class PerformanceScorecardSchema(Schema):
    overall_score: int
    work_reports_score: int
    punctuality_score: int
    rank_text: str  # e.g., "Rank #3 of 12 in IT"

class DepartmentRankingSchema(Schema):
    rank: int
    total_members: int

class DashboardSummarySchema(Schema):
    full_name: str
    job_title: str
    department_name: str
    scorecard: PerformanceScorecardSchema
    ranking: DepartmentRankingSchema

class WorkReportScoreSchema(Schema):
    work_report_score: int
    average_rating: float
    reports_submitted: int
    approved_reports: int


class PunctualityScoreSchema(Schema):
    total_days: int
    on_time_days: int
    late_days: int
    absent_days: int
    punctuality_score: int

class ScorecardDetailSchema(Schema):
    full_name: str
    job_title: str
    department_name: str
    overall_score: int
    rank_text: str
    work_report: WorkReportScoreSchema
    punctuality_report: PunctualityScoreSchema
