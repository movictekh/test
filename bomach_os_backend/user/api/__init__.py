from ninja import NinjaAPI, Swagger

from user.api.v1.auth import auth_api as auth_router
from user.api.v1.biometric import biometric_api as biometric_router
from user.api.v1.company import company_api as company_router
from user.api.v1.branch import branch_api as branch_router
from user.api.v1.others import orthers_api as orthers_router
from user.api.v1.employee import router as employee_router
from user.api.v1.audit_log import audit_log_api as audit_log_router
from user.api.v1.compliance import compliance_api as compliance_router
from user.api.v1.clients import clients_api as clients_router
from user.api.v1.client_inventory import inventory_api as inventory_router
from user.api.v1.wallet import wallet_api as wallet_router
from user.api.v1.cases import cases_api as cases_router
from user.api.v1.audit import audit_api as audit_router
from user.api.v1.shareholder import shareholder_api as shareholder_router
from user.api.v1.announcement import announcement_api as announcement_router
from user.api.v1.policy import policy_api as policy_router
from user.api.v1.meeting import meeting_api as meeting_router
from user.api.v1.board_resolution import board_resolution_api as board_resolution_router
from user.api.v1.approval import approval_api as approval_router
from user.api.v1.approval_queue import approval_queue_api as approval_queue_router
from user.api.v1.stats import stats_api as stats_router
from user.api.v1.event import events_api as events_router
from user.api.v1.loan import loan_api as loan_router
from user.api.v1.estate import estate_api as estate_router
from user.api.v1.brokerage import brokerage_api as brokerage_router
from user.api.v1.cart import cart_api as cart_router
from user.api.v1.estate_property_invoice import estate_invoice_api as estate_invoice_router
from user.api.v1.dashboard import employee_dashboard_api as employee_dashboard_router
from user.api.v1.role import role_api as role_router
from user.api.v1.drawing_bank import drawing_bank_api as drawing_bank_router
from user.api.v1.client_service import client_service_api as client_service_router
from user.api.v1.partner import partner_api as partner_router
from user.api.v1.target_report import target_report_api as target_report_router
from user.api.v1.notification import notification_router
from user.api.v1.command_center import command_center_router
from user.api.v1.workflow_rule import workflow_rule_router
from user.utils.auth import JWTAuthenticator

from user.api.v1.sops import dept_router, unit_router, resp_router, sop_dashboard_router

# Operations routers
from operations.api.v1 import dashboard as ops_dashboard, projects as ops_projects
from operations.api.v1 import tasks as ops_tasks, my_tasks as ops_my_tasks
from operations.api.v1 import worksites as ops_worksites
from operations.api.v1 import contracts as ops_contracts, timelines as ops_timelines
from operations.api.v1 import milestones as ops_milestones, site_equipment as ops_site_equipment

# Services routers
from services.api.v1 import (
    categories as svc_categories, content as svc_content,
    documents as svc_documents, expenses as svc_expenses,
    feedback as svc_feedback,
    invoices as svc_invoices, leads as svc_leads, marketing_campaigns as svc_marketing,
    orders as svc_orders, payments as svc_payments, property as svc_property,
    quotes as svc_quotes, reports as svc_reports, revenue_execution as svc_revenue_execution,
    service_leads as svc_service_leads, service_requests as svc_service_requests,
    services as svc_services, stats as svc_stats,
    funnel_router as svc_funnel, marketing_router as svc_marketing_cc,
    csrc_router as svc_csrc, pipeline_router as svc_pipeline,
)
from finance.api.v1 import (
    accounting as finance_accounting,
    accounts as finance_accounts,
    cashbook as finance_cashbook,
    cash_flow as finance_cash_flow,
    commissions as finance_commissions,
    expenses as finance_expenses,
    invoices as finance_invoices,
    payments as finance_payments,
    payroll as finance_payroll,
    petty_cash as finance_petty_cash,
    receivables as finance_receivables,
    service_orders as finance_service_orders,
    statutory as finance_statutory,
    vendors as finance_vendors,
    wallets as finance_wallets,
)

# HR

from hr.api.v1.dashboard import router as dashboard_router
from hr.api.v1.job_postings import router as job_postings_router
from hr.api.v1.applicants import router as applicants_router
from hr.api.v1.leave_requests import router as leave_requests_router
from hr.api.v1.performance_reviews import router as performance_reviews_router
from hr.api.v1.payroll import router as payroll_router
from hr.api.v1.training_programs import router as training_programs_router
from hr.api.v1.assets import router as assets_router
from hr.api.v1.award import router as award_router
from hr.api.v1.work_reports import router as work_reports_router
from hr.api.v1.disciplinary_cases import router as disciplinary_cases_router
from hr.api.v1.monthly_scorecards import router as monthly_scorecards_router
from hr.api.v1.employee_evaluations import router as employee_evaluations_router
from hr.api.v1.kpis import router as kpis_router
from hr.api.v1.interviews import router as interviews_router
from hr.api.v1.offer_letters import router as offer_letters_router



authenticator = JWTAuthenticator()

# Main API instance
api = NinjaAPI(
    auth=authenticator,
    docs_url="/docs/",
    title="BOMACH API",
    version="1.0.0",
    description="BOMACH Backend REST API for frontend integration",
    docs=Swagger(settings={"persistAuthorization": True}),
)

@api.get("/health", tags=["Health"], auth=None)
def health_check(request):
    """Health check endpoint"""
    return {"status": "healthy", "detail": "API is running"}

# === User routers ===
api.add_router("/auth/", auth_router)
api.add_router("/company/", company_router)
api.add_router("/branch/", branch_router)
api.add_router("/others/", orthers_router)
api.add_router("/employees/", employee_router)
api.add_router("/audit-logs/", audit_log_router)
api.add_router("/biometric/", biometric_router)
api.add_router("/compliance/", compliance_router)
api.add_router("/clients/", clients_router)
api.add_router("/inventory/", inventory_router)
api.add_router("/wallet/", wallet_router)
api.add_router("/cases/", cases_router)
api.add_router("/audits/", audit_router)
api.add_router("/shareholders/", shareholder_router)
api.add_router("/announcements/", announcement_router)
api.add_router("/policies/", policy_router)
api.add_router("/meetings/", meeting_router)
api.add_router("/board-resolutions/", board_resolution_router)
api.add_router("/approvals/", approval_router)
api.add_router("/approvals/queue/", approval_queue_router)
api.add_router("/stats/", stats_router)
api.add_router("/events/", events_router)
api.add_router("/loans", loan_router)
api.add_router("/estates/", estate_router)
api.add_router("/brokerage/", brokerage_router)
api.add_router("/estate-invoices/", estate_invoice_router)
api.add_router("/cart/", cart_router)
api.add_router("/dashboard/", employee_dashboard_router)
api.add_router("/roles/", role_router)
api.add_router("/drawing-bank/", drawing_bank_router)
api.add_router("/client-services/", client_service_router)
api.add_router("/service-requests/", svc_service_requests.router)
api.add_router("/partners/", partner_router)
api.add_router("/target-reports", target_report_router)
api.add_router("/notifications", notification_router)
api.add_router("/command-center", command_center_router)
api.add_router("/workflow-rules", workflow_rule_router)

# === HR routers ===

api.add_router('/dashboard', dashboard_router)
api.add_router('/job-postings', job_postings_router)
api.add_router('/applicants', applicants_router)
api.add_router('/leave-requests', leave_requests_router)
api.add_router('/performance-reviews', performance_reviews_router)
api.add_router('/payroll', payroll_router)
api.add_router('/training-programs', training_programs_router)
api.add_router('/assets', assets_router)
api.add_router('/awards', award_router)
api.add_router('/work-reports', work_reports_router)
api.add_router('/disciplinary-cases', disciplinary_cases_router)
api.add_router('/monthly-scorecards', monthly_scorecards_router)
api.add_router('/employee-evaluations', employee_evaluations_router)
api.add_router('/kpis', kpis_router)
api.add_router('/applicants', interviews_router)
api.add_router('/applicants', offer_letters_router)


# === Operations routers ===
api.add_router("/dashboard", ops_dashboard.router)
api.add_router("/projects", ops_projects.router)
api.add_router("/tasks", ops_tasks.router)
api.add_router("/my-tasks", ops_my_tasks.router)
api.add_router("/worksites", ops_worksites.router)
api.add_router("/contracts", ops_contracts.router)
api.add_router("/timelines", ops_timelines.router)
api.add_router("/milestones", ops_milestones.router)
api.add_router("/site-equipment", ops_site_equipment.router)

# === Services routers ===
api.add_router("/categories", svc_categories.router)
api.add_router("/content", svc_content.router)
api.add_router("/documents", svc_documents.router)

api.add_router("/expenses", svc_expenses.router)
api.add_router("/feedback", svc_feedback.router)
api.add_router("/reports", svc_reports.router)
api.add_router("/services", svc_services.router)
api.add_router("/leads", svc_leads.router)
api.add_router("/service-leads", svc_service_leads.router)
api.add_router("/quotes", svc_quotes.router)
api.add_router("/orders", svc_orders.router)
api.add_router("/invoices", svc_invoices.router)
api.add_router("/marketing-campaigns", svc_marketing.router)
api.add_router("/payments", svc_payments.router)
api.add_router("/properties", svc_property.router)
api.add_router("/revenue-execution", svc_revenue_execution.router)
api.add_router("/stats", svc_stats.router)

# === Finance routers ===
api.add_router("/finance", finance_accounting.router)
api.add_router("/finance", finance_invoices.router)
api.add_router("/finance", finance_accounts.router)
api.add_router("/finance", finance_payments.router)
api.add_router("/finance", finance_payroll.router)
api.add_router("/finance", finance_receivables.router)
api.add_router("/finance", finance_wallets.router)
api.add_router("/finance", finance_expenses.router)
api.add_router("/finance", finance_vendors.router)
api.add_router("/finance", finance_petty_cash.router)
api.add_router("/finance", finance_cashbook.router)
api.add_router("/finance", finance_cash_flow.router)
api.add_router("/finance", finance_commissions.router)
api.add_router("/finance", finance_service_orders.router)
api.add_router("/finance", finance_statutory.router)



api.add_router("/sop/departments", dept_router)
api.add_router("/sop/units", unit_router)
api.add_router("/sop/responsibilities", resp_router)
api.add_router("/sop/dashboard", sop_dashboard_router)

# === CRM & Sales Pipeline routers ===
api.add_router("/", svc_funnel)
api.add_router("/", svc_marketing_cc)
api.add_router("/", svc_csrc)
api.add_router("/", svc_pipeline)
