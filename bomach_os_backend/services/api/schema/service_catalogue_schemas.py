from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from ninja import Schema


class FieldTypeOut(Schema):
    value: str
    label: str
    supports_options: bool
    supports_validation: bool


class ServiceCreateSchema(Schema):
    name: str
    code: Optional[str] = None
    category_id: int
    division: Optional[str] = ""
    description: str
    base_price: Decimal = Decimal("0.00")
    delivery_time: Optional[str] = ""
    status: str = "draft"
    owner_role_id: Optional[int] = None
    default_sla_days: int = 0
    fulfillment_mode: Optional[str] = ""
    client_visibility: str = "visible"
    created_by_id: Optional[int] = None


class ServiceUpdateSchema(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    category_id: Optional[int] = None
    division: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[Decimal] = None
    delivery_time: Optional[str] = None
    status: Optional[str] = None
    owner_role_id: Optional[int] = None
    default_sla_days: Optional[int] = None
    fulfillment_mode: Optional[str] = None
    client_visibility: Optional[str] = None


class ServiceCoreOut(Schema):
    id: int
    code: Optional[str] = None
    name: str
    category_id: int
    category_name: str
    division: str
    description: str
    base_price: Decimal
    delivery_time: str
    status: str
    owner_role_id: Optional[int] = None
    owner_role_name: str
    default_sla_days: int
    fulfillment_mode: str
    client_visibility: str
    active_request_form_id: Optional[int] = None
    active_pricing_config_id: Optional[int] = None
    active_workflow_id: Optional[int] = None
    subservice_count: int = 0
    branch_activation_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by_id: int


class ServiceSubServiceIn(Schema):
    code: Optional[str] = None
    name: str
    description: Optional[str] = ""
    status: str = "active"
    default_sla_days: int = 0
    sort_order: int = 0


class ServiceSubServiceUpdate(Schema):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    default_sla_days: Optional[int] = None
    sort_order: Optional[int] = None


class ServiceSubServiceBulkReplace(Schema):
    subservices: List[ServiceSubServiceIn]


class RequestFieldIn(Schema):
    key: str
    label: str
    field_type: str
    required: bool = False
    options: List[Any] = []
    validation: dict = {}
    help_text: Optional[str] = ""
    placeholder: Optional[str] = ""
    sort_order: int = 0


class RequestFormIn(Schema):
    name: str
    version: int = 1
    status: str = "draft"
    is_active: bool = False
    fields: List[RequestFieldIn] = []
    created_by_id: Optional[int] = None


class RequestFormUpdate(Schema):
    name: Optional[str] = None
    version: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    fields: Optional[List[RequestFieldIn]] = None


class PricingFieldIn(Schema):
    key: str
    label: str
    field_type: str
    default_value: Optional[Any] = None
    required: bool = False
    options: List[Any] = []
    validation: dict = {}
    sort_order: int = 0


class PricingConfigIn(Schema):
    name: str
    version: int = 1
    pricing_type: str
    formula: Optional[str] = ""
    tax_rate: Decimal = Decimal("0.00")
    deposit_percent: Decimal = Decimal("0.00")
    discount_approval_threshold_percent: Decimal = Decimal("0.00")
    status: str = "draft"
    is_active: bool = False
    fields: List[PricingFieldIn] = []
    created_by_id: Optional[int] = None


class PricingConfigUpdate(Schema):
    name: Optional[str] = None
    version: Optional[int] = None
    pricing_type: Optional[str] = None
    formula: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    deposit_percent: Optional[Decimal] = None
    discount_approval_threshold_percent: Optional[Decimal] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    fields: Optional[List[PricingFieldIn]] = None


class WorkflowStageIn(Schema):
    name: str
    owner_role_id: Optional[int] = None
    sla_days: int = 0
    requires_approval: bool = False
    requires_evidence: bool = False
    client_visible: bool = False
    sort_order: int = 0


class WorkflowSeedIn(Schema):
    name: str = "Default Workflow"
    version: int = 1
    status: str = "draft"
    is_active: bool = False
    stages: List[WorkflowStageIn]
    created_by_id: Optional[int] = None


class WorkflowIn(Schema):
    name: str
    version: int = 1
    status: str = "draft"
    is_active: bool = False
    stages: List[WorkflowStageIn] = []
    created_by_id: Optional[int] = None


class WorkflowUpdate(Schema):
    name: Optional[str] = None
    version: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    stages: Optional[List[WorkflowStageIn]] = None


class WorkflowStageUpdate(Schema):
    name: Optional[str] = None
    owner_role_id: Optional[int] = None
    sla_days: Optional[int] = None
    requires_approval: Optional[bool] = None
    requires_evidence: Optional[bool] = None
    client_visible: Optional[bool] = None
    sort_order: Optional[int] = None


class WorkflowStageBulkReplace(Schema):
    stages: List[WorkflowStageIn]


class BranchActivationIn(Schema):
    branch_id: int
    status: str = "active"
    client_visible: bool = True
    capacity: Optional[int] = None
    activated_at: Optional[datetime] = None


class BranchActivationBulkUpsert(Schema):
    branch_activations: List[BranchActivationIn]


class ServicePublishIn(Schema):
    status: str = "active"
    client_visibility: Optional[str] = None
    request_form_id: Optional[int] = None
    pricing_config_id: Optional[int] = None
    workflow_id: Optional[int] = None
