from ninja import Schema


class FileUploadResponseSchema(Schema):
    """Schema for file upload response"""
    url: str

class MessageSchema(Schema):
    """Schema for success/error messages"""
    detail: str


class DashboardStatsSchema(Schema):
    total_employees: int
    new_employees_count: int
    total_branches: int
    removed_branches_count: int
    pending_approvals: int
    overdue_tasks_count: int
    asset_inventory: int
    new_inventory_count: int
