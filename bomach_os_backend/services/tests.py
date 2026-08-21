import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from domains.marketing_sales.models.content import (
    Content,
    ContentCalendarItem,
    MediaLibraryAsset,
)
from domains.marketing_sales.models.marketing import (
    CampaignAsset,
    CampaignExpense,
    CampaignRequest,
    CampaignRisk,
    EmailMarketingCampaign,
    EmailMarketingRecipient,
    MarketingCampaign,
    MarketingMeetingAction,
    MarketingMeetingContext,
    PartnerCommission,
    PartnerInvitation,
    PartnerReport,
    PartnerTask,
    TraditionalMediaPlacement,
)
from domains.marketing_sales.models.revenue_execution import (
    DailyActionInstance,
    RevenueKeyResult,
    RevenueObjective,
    TurnaroundPlan,
)
from domains.marketing_sales.models.sales import (
    Lead,
    LeadActivity,
    LeadFunnelEvent,
    SalesPlaybook,
    SalesPlaybookObjection,
)
from domains.marketing_sales.services.funnel import backfill_lead_funnel_events
from finance.models import FinanceAccount
from services.models.service import (
    Quote,
    Service,
    ServiceBranchActivation,
    ServiceCategory,
    ServiceDeliverable,
    ServiceExecutionTask,
    ServiceLead,
    ServiceOrder,
    ServiceOrderActivity,
    ServiceOrderMilestone,
    ServicePricingConfig,
    ServicePricingField,
    ServiceRequest,
    ServiceRequestActivity,
    ServiceRequestAnswer,
    ServiceRequestAttachment,
    ServiceRequestField,
    ServiceRequestForm,
    ServiceSubService,
    ServiceWorkflow,
    ServiceWorkflowStage,
)
from user.models.branch import Branch
from user.models.client import Client as CustomerClient
from user.models.employee import Employee
from user.models.meeting import Meeting
from user.models.partner import Partner
from user.models.role import Role
from user.models.role_targets import (
    EmployeeTarget,
    EmployeeTargetReport,
    RoleTargetTemplate,
)
from user.models.user import User
from user.services.jwt_service import JWTService


class ServiceCatalogueModelTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(
            name="Service Owner", permissions={"services": ["create", "view", "list"]}
        )
        self.user = User.objects.create_user(
            email="catalogue.owner@example.com",
            username="catalogueowner",
            password="password123",
        )
        self.category = ServiceCategory.objects.create(
            name=ServiceCategory.CategoryChoices.SURVEYING,
            description="Surveying services",
        )
        self.service = Service.objects.create(
            code="SUR-CAD",
            name="Cadastral Land Survey",
            category=self.category,
            division="Land Surveying & Geospatial",
            description="Boundary survey, beacon placement and processing.",
            base_price=Decimal("250000.00"),
            delivery_time="14 days",
            status="active",
            owner_role=self.role,
            default_sla_days=14,
            fulfillment_mode="quick_order",
            client_visibility="visible",
            created_by=self.user,
        )

    def make_branch(self):
        return Branch.objects.create(
            branch_name="Enugu Branch",
            country="Nigeria",
            state="Enugu",
            city="Enugu",
            office_address="1 Test Road",
            contact_email="enugu@example.com",
            contact_phone="+2348012345678",
        )

    def test_service_catalogue_configuration_models_can_be_created(self):
        subservice = ServiceSubService.objects.create(
            service=self.service,
            code="PERIMETER",
            name="Perimeter Survey",
            description="Boundary perimeter survey.",
            default_sla_days=7,
            sort_order=1,
        )
        request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Default Survey Intake",
            version=1,
            status="active",
            is_active=True,
            created_by=self.user,
        )
        request_field = ServiceRequestField.objects.create(
            form=request_form,
            key="plot-size",
            label="Plot size",
            field_type="number",
            required=True,
            validation={"min": 1},
            sort_order=1,
        )
        pricing_config = ServicePricingConfig.objects.create(
            service=self.service,
            name="Survey Fee Calculator",
            version=1,
            pricing_type="formula",
            formula="base_fee + plot_size * area_rate",
            deposit_percent=Decimal("70.00"),
            status="active",
            is_active=True,
            created_by=self.user,
        )
        pricing_field = ServicePricingField.objects.create(
            pricing_config=pricing_config,
            key="base-fee",
            label="Base fee",
            field_type="money",
            default_value="250000",
            required=True,
            sort_order=1,
        )
        workflow = ServiceWorkflow.objects.create(
            service=self.service,
            name="Survey Fulfillment",
            version=1,
            status="active",
            is_active=True,
            created_by=self.user,
        )
        stage = ServiceWorkflowStage.objects.create(
            workflow=workflow,
            name="Schedule Fieldwork",
            owner_role=self.role,
            sla_days=2,
            requires_evidence=True,
            client_visible=True,
            sort_order=1,
        )
        branch_activation = ServiceBranchActivation.objects.create(
            service=self.service,
            branch=self.make_branch(),
            status="active",
            client_visible=True,
            capacity=10,
            activated_at=timezone.now(),
        )

        self.service.active_request_form = request_form
        self.service.active_pricing_config = pricing_config
        self.service.active_workflow = workflow
        self.service.save()
        self.service.refresh_from_db()

        self.assertEqual(subservice.service, self.service)
        self.assertEqual(request_field.form, request_form)
        self.assertEqual(pricing_field.pricing_config, pricing_config)
        self.assertEqual(stage.owner_role, self.role)
        self.assertEqual(branch_activation.branch.branch_name, "Enugu Branch")
        self.assertEqual(self.service.active_request_form, request_form)
        self.assertEqual(self.service.active_pricing_config, pricing_config)
        self.assertEqual(self.service.active_workflow, workflow)

    def test_only_one_active_request_form_pricing_config_and_workflow_per_service(self):
        ServiceRequestForm.objects.create(
            service=self.service,
            name="Survey Intake v1",
            version=1,
            status="active",
            is_active=True,
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceRequestForm.objects.create(
                    service=self.service,
                    name="Survey Intake v2",
                    version=2,
                    status="active",
                    is_active=True,
                    created_by=self.user,
                )

        ServicePricingConfig.objects.create(
            service=self.service,
            name="Survey Pricing v1",
            version=1,
            pricing_type="formula",
            status="active",
            is_active=True,
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServicePricingConfig.objects.create(
                    service=self.service,
                    name="Survey Pricing v2",
                    version=2,
                    pricing_type="formula",
                    status="active",
                    is_active=True,
                    created_by=self.user,
                )

        ServiceWorkflow.objects.create(
            service=self.service,
            name="Survey Workflow v1",
            version=1,
            status="active",
            is_active=True,
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceWorkflow.objects.create(
                    service=self.service,
                    name="Survey Workflow v2",
                    version=2,
                    status="active",
                    is_active=True,
                    created_by=self.user,
                )

    def test_field_keys_are_unique_within_their_parent_configuration(self):
        request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Default Survey Intake",
            version=1,
            created_by=self.user,
        )
        ServiceRequestField.objects.create(
            form=request_form,
            key="site-location",
            label="Site location",
            field_type="location",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceRequestField.objects.create(
                    form=request_form,
                    key="site-location",
                    label="Site location duplicate",
                    field_type="text",
                )

        pricing_config = ServicePricingConfig.objects.create(
            service=self.service,
            name="Survey Pricing",
            version=1,
            pricing_type="formula",
            created_by=self.user,
        )
        ServicePricingField.objects.create(
            pricing_config=pricing_config,
            key="plot-size",
            label="Plot size",
            field_type="number",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServicePricingField.objects.create(
                    pricing_config=pricing_config,
                    key="plot-size",
                    label="Plot size duplicate",
                    field_type="number",
                )


class CommercialServiceRequestModelTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            email="request.staff@example.com",
            username="requeststaff",
            password="password123",
        )
        self.client_user = User.objects.create_user(
            email="request.client@example.com",
            username="requestclient",
            password="password123",
            first_name="Ada",
            last_name="Okoro",
        )
        self.customer = CustomerClient.objects.create(
            user=self.client_user, phone="+2348012345678"
        )
        self.role = Role.objects.create(
            name="Commercial Owner",
            permissions={"service_requests": ["create", "view"]},
        )
        self.category = ServiceCategory.objects.create(
            name=ServiceCategory.CategoryChoices.SURVEYING,
            description="Surveying services",
        )
        self.service = Service.objects.create(
            code="SUR-COM",
            name="Commercial Survey",
            category=self.category,
            division="Land Surveying & Geospatial",
            description="Survey intake for commercial flow.",
            base_price=Decimal("250000.00"),
            delivery_time="14 days",
            status="active",
            owner_role=self.role,
            default_sla_days=7,
            fulfillment_mode="managed_case",
            client_visibility="visible",
            created_by=self.staff_user,
        )
        self.subservice = ServiceSubService.objects.create(
            service=self.service,
            code="BOUNDARY",
            name="Boundary Survey",
        )
        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Commercial Survey Intake",
            version=1,
            status="active",
            is_active=True,
            created_by=self.staff_user,
        )
        self.fields = {
            "site-location": ServiceRequestField.objects.create(
                form=self.request_form,
                key="site-location",
                label="Site location",
                field_type="location",
                required=True,
                sort_order=1,
            ),
            "plot-size": ServiceRequestField.objects.create(
                form=self.request_form,
                key="plot-size",
                label="Plot size",
                field_type="number",
                required=True,
                sort_order=2,
            ),
            "inspection-date": ServiceRequestField.objects.create(
                form=self.request_form,
                key="inspection-date",
                label="Inspection date",
                field_type="date",
                required=True,
                sort_order=3,
            ),
            "contact-email": ServiceRequestField.objects.create(
                form=self.request_form,
                key="contact-email",
                label="Contact email",
                field_type="email",
                required=True,
                sort_order=4,
            ),
            "package": ServiceRequestField.objects.create(
                form=self.request_form,
                key="package",
                label="Package",
                field_type="select",
                required=True,
                options=["standard", "premium"],
                sort_order=5,
            ),
            "tags": ServiceRequestField.objects.create(
                form=self.request_form,
                key="tags",
                label="Tags",
                field_type="multiselect",
                options=[
                    {"value": "urgent", "label": "Urgent"},
                    {"value": "title", "label": "Title"},
                ],
                sort_order=6,
            ),
            "consent": ServiceRequestField.objects.create(
                form=self.request_form,
                key="consent",
                label="Consent",
                field_type="checkbox",
                required=True,
                sort_order=7,
            ),
            "documents": ServiceRequestField.objects.create(
                form=self.request_form,
                key="documents",
                label="Documents",
                field_type="file",
                sort_order=8,
            ),
        }
        self.pricing_config = ServicePricingConfig.objects.create(
            service=self.service,
            name="Commercial Survey Pricing",
            version=1,
            pricing_type="fixed",
            status="active",
            is_active=True,
            created_by=self.staff_user,
        )
        self.workflow = ServiceWorkflow.objects.create(
            service=self.service,
            name="Commercial Survey Workflow",
            version=1,
            status="active",
            is_active=True,
            created_by=self.staff_user,
        )
        self.service.active_request_form = self.request_form
        self.service.active_pricing_config = self.pricing_config
        self.service.active_workflow = self.workflow
        self.service.save()

    def valid_answers(self, **overrides):
        answers = {
            "site-location": {"address": "Independence Layout, Enugu"},
            "plot-size": "500",
            "inspection-date": "2026-08-20",
            "contact-email": "client@example.com",
            "package": "standard",
            "tags": ["urgent"],
            "consent": True,
            "documents": ["https://example.com/title.pdf"],
        }
        answers.update(overrides)
        return answers

    def make_request(self, **overrides):
        data = {
            "client": self.customer,
            "service": self.service,
            "subservice": self.subservice,
            "contact_name": "Ada Okoro",
            "contact_phone": "+2348012345678",
            "contact_email": "client@example.com",
            "customer_type": "individual",
            "source": "client_portal",
            "status": "new",
            "priority": "normal",
            "budget": Decimal("750000.00"),
            "estimated_value": Decimal("650000.00"),
            "preferred_date": "2026-08-20",
            "due_date": "2026-08-25",
            "next_action": "Review and assign request",
            "scope_summary": "Boundary survey for a commercial request.",
            "answers_snapshot": self.valid_answers(),
            "created_by": self.staff_user,
            "submitted_by": self.client_user,
        }
        data.update(overrides)
        return ServiceRequest.objects.create(**data)

    def make_branch(self):
        return Branch.objects.create(
            branch_name="Commercial Branch",
            country="Nigeria",
            state="Enugu",
            city="Enugu",
            office_address="2 Commercial Road",
            contact_email="commercial@example.com",
            contact_phone="+2348098765432",
        )

    def test_request_number_generation_and_configuration_snapshots(self):
        first = self.make_request()
        second = self.make_request(contact_email="second@example.com")

        self.assertRegex(first.request_number, r"^REQ-\d{8}-001$")
        self.assertRegex(second.request_number, r"^REQ-\d{8}-002$")
        self.assertEqual(first.request_form, self.request_form)
        self.assertEqual(first.request_form_version, 1)
        self.assertEqual(first.pricing_config, self.pricing_config)
        self.assertEqual(first.pricing_config_version, 1)
        self.assertEqual(first.workflow, self.workflow)
        self.assertEqual(first.workflow_version, 1)
        self.assertEqual(first.form_snapshot["fields"][0]["key"], "site-location")

    def test_required_answer_validation_failure(self):
        answers = self.valid_answers()
        answers.pop("site-location")

        with self.assertRaises(ValidationError) as context:
            self.make_request(answers_snapshot=answers)

        self.assertIn("answers_snapshot", context.exception.message_dict)

    def test_select_and_multiselect_option_validation(self):
        with self.assertRaises(ValidationError):
            self.make_request(answers_snapshot=self.valid_answers(package="enterprise"))

        with self.assertRaises(ValidationError):
            self.make_request(
                answers_snapshot=self.valid_answers(tags=["urgent", "unknown"])
            )

    def test_basic_type_validation(self):
        invalid_cases = [
            {"plot-size": "not-a-number"},
            {"inspection-date": "20-08-2026"},
            {"contact-email": "not-an-email"},
            {"consent": "yes"},
        ]

        for answer_override in invalid_cases:
            with self.subTest(answer_override=answer_override):
                with self.assertRaises(ValidationError):
                    self.make_request(
                        answers_snapshot=self.valid_answers(**answer_override)
                    )

    def test_form_snapshot_is_preserved_after_form_changes(self):
        request = self.make_request()
        original_label = request.form_snapshot["fields"][0]["label"]
        self.fields["site-location"].label = "Updated site location"
        self.fields["site-location"].save()

        request.next_action = "Continue review"
        request.save()
        request.refresh_from_db()

        self.assertEqual(request.form_snapshot["fields"][0]["label"], original_label)
        self.assertEqual(
            request.answers_snapshot["site-location"],
            {"address": "Independence Layout, Enugu"},
        )

    def test_optional_source_links_can_be_attached(self):
        branch = self.make_branch()
        service_lead = ServiceLead.objects.create(
            client=self.customer,
            service=self.service,
            estimated_value=Decimal("900000.00"),
            created_by=self.staff_user,
        )
        crm_lead = Lead.objects.create(
            full_name="Ada Okoro",
            phone="+2348012345678",
            email="lead@example.com",
            division="surveying",
            source="website_form",
            estimated_value=Decimal("900000.00"),
            created_by=self.staff_user,
        )

        request = self.make_request(
            branch=branch,
            service_lead=service_lead,
            crm_lead=crm_lead,
            source="sales_crm",
            source_reference="CAMPAIGN-001",
        )

        self.assertEqual(request.branch, branch)
        self.assertEqual(request.service_lead, service_lead)
        self.assertEqual(request.crm_lead, crm_lead)
        self.assertEqual(request.subservice, self.subservice)

    def test_answers_attachments_and_activity_journal(self):
        request = self.make_request()
        answer = ServiceRequestAnswer.objects.create(
            request=request,
            field=self.fields["site-location"],
            field_key="site-location",
            label="Site location",
            field_type="location",
            value={"address": "Independence Layout, Enugu"},
            sort_order=1,
        )
        attachment = ServiceRequestAttachment.objects.create(
            request=request,
            field_key="documents",
            label="Title document",
            file_name="title.pdf",
            file_url="https://example.com/title.pdf",
            uploaded_by=self.staff_user,
        )
        first_activity = ServiceRequestActivity.objects.create(
            request=request,
            activity_type="request_created",
            note="Request submitted and consent recorded.",
            created_by=self.staff_user,
        )
        second_activity = ServiceRequestActivity.objects.create(
            request=request,
            activity_type="assessment_scheduled",
            outcome="follow_up_scheduled",
            note="Assessment scheduled.",
            created_by=self.staff_user,
        )

        self.assertEqual(request.answers.get(), answer)
        self.assertEqual(request.attachments.get(), attachment)
        self.assertEqual(
            list(request.activities.all()), [second_activity, first_activity]
        )

    def test_status_and_priority_choice_validation(self):
        with self.assertRaises(ValidationError):
            self.make_request(status="pending")

        with self.assertRaises(ValidationError):
            self.make_request(priority="urgent")

    def test_quote_link_can_be_attached_without_order_conversion(self):
        request = self.make_request()
        quote = Quote.objects.create(
            client=self.customer,
            service=self.service,
            description="Commercial survey quote",
            amount=Decimal("650000.00"),
            valid_until=timezone.localdate() + timedelta(days=14),
            status="sent",
            created_by=self.staff_user,
        )

        request.quote = quote
        request.status = "quoted"
        request.save()
        request.refresh_from_db()

        self.assertEqual(request.quote, quote)
        self.assertEqual(request.status, "quoted")

    def test_quote_breakdown_calculation_and_rejected_immutability(self):
        request = self.make_request()
        quote = Quote.objects.create(
            client=self.customer,
            service=self.service,
            service_request=request,
            description="Commercial survey quote",
            service_fee=Decimal("650000.00"),
            other_charges=Decimal("50000.00"),
            discount=Decimal("25000.00"),
            tax_rate=Decimal("7.50"),
            deposit_percent=Decimal("30.00"),
            valid_until=timezone.localdate() + timedelta(days=14),
            status="awaiting_approval",
            required_approver_role=self.role,
            created_by=self.staff_user,
        )

        self.assertEqual(quote.subtotal, Decimal("700000.00"))
        self.assertEqual(quote.tax_amount, Decimal("50625.00"))
        self.assertEqual(quote.amount, Decimal("725625.00"))
        self.assertEqual(quote.deposit_amount, Decimal("217687.50"))

        quote.status = "rejected"
        quote.client_rejection_reason = "Please revise scope."
        quote.client_responded_at = timezone.now()
        quote.save()

        quote.required_approver_role = None
        with self.assertRaises(ValidationError):
            quote.save()


class ServiceCatalogueAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(
            name="Service Catalogue Manager",
            permissions={
                "services": ["create", "view", "list", "update", "delete"],
                "service_subservices": ["create", "view", "list", "update", "delete"],
                "service_request_forms": ["create", "view", "list", "update", "delete"],
                "service_pricing_configs": [
                    "create",
                    "view",
                    "list",
                    "update",
                    "delete",
                ],
                "service_branch_activations": [
                    "create",
                    "view",
                    "list",
                    "update",
                    "delete",
                ],
                "service_workflows": ["create", "view", "list", "update", "delete"],
            },
        )
        self.user = User.objects.create_user(
            email="catalogue.manager@example.com",
            username="cataloguemanager",
            password="password123",
        )
        Employee.objects.create(
            user=self.user,
            employee_id="EMP-CATALOGUE-001",
            role=self.role,
            is_active=True,
        )
        token = JWTService.create_tokens(self.user.id)["access"]
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        self.category = ServiceCategory.objects.create(
            name=ServiceCategory.CategoryChoices.CONSTRUCTION,
            description="Construction services",
        )
        self.branch = Branch.objects.create(
            branch_name="Lagos Branch",
            country="Nigeria",
            state="Lagos",
            city="Lagos",
            office_address="1 Test Avenue",
            contact_email="lagos@example.com",
            contact_phone="+2348012345678",
        )

    def post_json(self, path, data):
        return self.client.post(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **self.headers,
        )

    def put_json(self, path, data):
        return self.client.put(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **self.headers,
        )

    def test_incremental_wizard_flow_creates_and_publishes_service(self):
        service_response = self.post_json(
            "/api/v1/services",
            {
                "name": "Building Construction",
                "code": "ENG-BLD",
                "category_id": self.category.id,
                "division": "Engineering & Construction",
                "description": "Design-to-delivery construction.",
                "base_price": "100000.00",
                "delivery_time": "7 days",
                "owner_role_id": self.role.id,
                "default_sla_days": 7,
                "fulfillment_mode": "project_worksite",
                "client_visibility": "visible",
            },
        )
        self.assertEqual(service_response.status_code, 201)
        service_id = service_response.json()["id"]
        self.assertEqual(service_response.json()["status"], "draft")

        subservices_response = self.put_json(
            f"/api/v1/services/{service_id}/subservices",
            {
                "subservices": [
                    {
                        "code": "FOUNDATION",
                        "name": "Foundation to Roofing",
                        "sort_order": 1,
                    },
                    {"code": "RENOVATION", "name": "Renovation", "sort_order": 2},
                ]
            },
        )
        self.assertEqual(subservices_response.status_code, 200)
        self.assertEqual(len(subservices_response.json()), 2)

        form_response = self.post_json(
            f"/api/v1/services/{service_id}/request-forms",
            {
                "name": "Construction Intake",
                "version": 1,
                "status": "draft",
                "is_active": True,
                "fields": [
                    {
                        "key": "client-name",
                        "label": "Client name",
                        "field_type": "text",
                        "required": True,
                        "sort_order": 1,
                    },
                    {
                        "key": "project-location",
                        "label": "Project location",
                        "field_type": "location",
                        "required": True,
                        "sort_order": 2,
                    },
                ],
            },
        )
        self.assertEqual(form_response.status_code, 201)
        form_id = form_response.json()["id"]
        self.assertTrue(form_response.json()["is_active"])

        pricing_response = self.post_json(
            f"/api/v1/services/{service_id}/pricing-configs",
            {
                "name": "Construction Estimate",
                "version": 1,
                "pricing_type": "formula",
                "formula": "floor_area * construction_rate + preliminaries",
                "tax_rate": "7.50",
                "deposit_percent": "30.00",
                "discount_approval_threshold_percent": "3.00",
                "status": "draft",
                "is_active": True,
                "fields": [
                    {
                        "key": "floor-area",
                        "label": "Floor area",
                        "field_type": "number",
                        "required": True,
                        "sort_order": 1,
                    },
                    {
                        "key": "construction-rate",
                        "label": "Construction rate",
                        "field_type": "money",
                        "required": True,
                        "sort_order": 2,
                    },
                ],
            },
        )
        self.assertEqual(pricing_response.status_code, 201)
        pricing_config_id = pricing_response.json()["id"]
        self.assertTrue(pricing_response.json()["is_active"])

        workflow_response = self.post_json(
            f"/api/v1/services/{service_id}/workflow-seed",
            {
                "name": "Construction Workflow",
                "version": 1,
                "status": "draft",
                "is_active": True,
                "stages": [
                    {
                        "name": "Request Review",
                        "owner_role_id": self.role.id,
                        "sort_order": 1,
                    },
                    {
                        "name": "Site Assessment",
                        "owner_role_id": self.role.id,
                        "requires_evidence": True,
                        "sort_order": 2,
                    },
                ],
            },
        )
        self.assertEqual(workflow_response.status_code, 201)
        workflow_id = workflow_response.json()["id"]
        self.assertTrue(workflow_response.json()["is_active"])

        branch_response = self.put_json(
            f"/api/v1/services/{service_id}/branch-activations",
            {
                "branch_activations": [
                    {
                        "branch_id": self.branch.id,
                        "status": "active",
                        "client_visible": True,
                        "capacity": 4,
                    }
                ]
            },
        )
        self.assertEqual(branch_response.status_code, 200)
        self.assertEqual(branch_response.json()[0]["branch_id"], self.branch.id)

        publish_response = self.post_json(
            f"/api/v1/services/{service_id}/publish",
            {
                "status": "active",
                "client_visibility": "visible",
                "request_form_id": form_id,
                "pricing_config_id": pricing_config_id,
                "workflow_id": workflow_id,
            },
        )
        self.assertEqual(publish_response.status_code, 200)
        self.assertEqual(publish_response.json()["status"], "active")
        self.assertEqual(publish_response.json()["active_request_form_id"], form_id)
        self.assertEqual(
            publish_response.json()["active_pricing_config_id"], pricing_config_id
        )
        self.assertEqual(publish_response.json()["active_workflow_id"], workflow_id)

        detail_response = self.client.get(
            f"/api/v1/services/catalogue/{service_id}", **self.headers
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(len(detail["subservices"]), 2)
        self.assertEqual(len(detail["request_forms"][0]["fields"]), 2)
        self.assertEqual(len(detail["pricing_configs"][0]["fields"]), 2)
        self.assertEqual(len(detail["workflows"][0]["stages"]), 2)
        self.assertEqual(len(detail["branch_activations"]), 1)

    def test_request_field_types_endpoint_uses_backend_registry(self):
        response = self.client.get(
            "/api/v1/services/request-field-types", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        values = {item["value"] for item in response.json()}
        self.assertIn("text", values)
        self.assertIn("money", values)
        self.assertIn("location", values)

    def test_form_update_rejects_duplicate_field_keys(self):
        service = Service.objects.create(
            code="ENG-INS",
            name="Structural Inspection",
            category=self.category,
            division="Engineering & Construction",
            description="Professional inspection.",
            base_price=Decimal("1000.00"),
            delivery_time="5 days",
            created_by=self.user,
        )
        form_response = self.post_json(
            f"/api/v1/services/{service.id}/request-forms",
            {
                "name": "Inspection Intake",
                "fields": [
                    {
                        "key": "site-address",
                        "label": "Site address",
                        "field_type": "text",
                    },
                ],
            },
        )
        self.assertEqual(form_response.status_code, 201)
        duplicate_response = self.put_json(
            f"/api/v1/services/{service.id}/request-forms/{form_response.json()['id']}",
            {
                "fields": [
                    {
                        "key": "site-address",
                        "label": "Site address",
                        "field_type": "text",
                    },
                    {"key": "site-address", "label": "Duplicate", "field_type": "text"},
                ],
            },
        )
        self.assertEqual(duplicate_response.status_code, 400)

    def test_workflow_designer_crud_activation_and_stage_management(self):
        service = Service.objects.create(
            code="ENG-WF",
            name="Workflow Managed Service",
            category=self.category,
            division="Engineering & Construction",
            description="Workflow test service.",
            base_price=Decimal("1000.00"),
            delivery_time="5 days",
            created_by=self.user,
        )
        other_service = Service.objects.create(
            code="ENG-OTHER",
            name="Other Workflow Service",
            category=self.category,
            division="Engineering & Construction",
            description="Other workflow test service.",
            base_price=Decimal("1000.00"),
            delivery_time="5 days",
            created_by=self.user,
        )

        create_response = self.post_json(
            f"/api/v1/services/{service.id}/workflows",
            {
                "name": "Primary Workflow",
                "version": 1,
                "status": "draft",
                "is_active": True,
                "stages": [
                    {
                        "name": "Request Review",
                        "owner_role_id": self.role.id,
                        "sla_days": 1,
                        "sort_order": 1,
                    },
                    {
                        "name": "Execution",
                        "owner_role_id": self.role.id,
                        "sla_days": 3,
                        "requires_evidence": True,
                        "sort_order": 2,
                    },
                ],
            },
        )
        self.assertEqual(create_response.status_code, 201)
        workflow_id = create_response.json()["id"]
        self.assertTrue(create_response.json()["is_active"])
        self.assertEqual(len(create_response.json()["stages"]), 2)
        service.refresh_from_db()
        self.assertEqual(service.active_workflow_id, workflow_id)

        list_response = self.client.get(
            f"/api/v1/services/{service.id}/workflows", **self.headers
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["id"], workflow_id)

        detail_response = self.client.get(
            f"/api/v1/services/{service.id}/workflows/{workflow_id}", **self.headers
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(
            detail_response.json()["stages"][0]["owner_role_name"], self.role.name
        )

        metadata_update = self.put_json(
            f"/api/v1/services/{service.id}/workflows/{workflow_id}",
            {"name": "Primary Workflow v1", "status": "draft"},
        )
        self.assertEqual(metadata_update.status_code, 200)
        self.assertEqual(metadata_update.json()["name"], "Primary Workflow v1")
        self.assertEqual(len(metadata_update.json()["stages"]), 2)

        replace_response = self.put_json(
            f"/api/v1/services/{service.id}/workflows/{workflow_id}/stages",
            {
                "stages": [
                    {
                        "name": "Scope Review",
                        "owner_role_id": self.role.id,
                        "sla_days": 2,
                        "sort_order": 1,
                    },
                    {
                        "name": "Client Acceptance",
                        "client_visible": True,
                        "sort_order": 2,
                    },
                ]
            },
        )
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(len(replace_response.json()), 2)
        self.assertEqual(replace_response.json()[0]["name"], "Scope Review")

        stage_response = self.post_json(
            f"/api/v1/services/{service.id}/workflows/{workflow_id}/stages",
            {
                "name": "Feedback",
                "owner_role_id": self.role.id,
                "sla_days": 1,
                "client_visible": True,
                "sort_order": 3,
            },
        )
        self.assertEqual(stage_response.status_code, 201)
        stage_id = stage_response.json()["id"]

        stage_update = self.put_json(
            f"/api/v1/services/{service.id}/workflows/{workflow_id}/stages/{stage_id}",
            {"name": "Completion Feedback", "requires_evidence": True},
        )
        self.assertEqual(stage_update.status_code, 200)
        self.assertEqual(stage_update.json()["name"], "Completion Feedback")
        self.assertTrue(stage_update.json()["requires_evidence"])

        stage_delete = self.client.delete(
            f"/api/v1/services/{service.id}/workflows/{workflow_id}/stages/{stage_id}",
            **self.headers,
        )
        self.assertEqual(stage_delete.status_code, 200)

        second_response = self.post_json(
            f"/api/v1/services/{service.id}/workflows",
            {
                "name": "Replacement Workflow",
                "version": 2,
                "status": "draft",
                "stages": [{"name": "New Review", "sort_order": 1}],
            },
        )
        self.assertEqual(second_response.status_code, 201)
        second_workflow_id = second_response.json()["id"]

        activate_response = self.post_json(
            f"/api/v1/services/{service.id}/workflows/{second_workflow_id}/activate",
            {},
        )
        self.assertEqual(activate_response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.active_workflow_id, second_workflow_id)
        self.assertFalse(ServiceWorkflow.objects.get(id=workflow_id).is_active)

        wrong_service_response = self.client.get(
            f"/api/v1/services/{other_service.id}/workflows/{second_workflow_id}",
            **self.headers,
        )
        self.assertEqual(wrong_service_response.status_code, 404)

        delete_response = self.client.delete(
            f"/api/v1/services/{service.id}/workflows/{second_workflow_id}",
            **self.headers,
        )
        self.assertEqual(delete_response.status_code, 200)
        archived = ServiceWorkflow.objects.get(id=second_workflow_id)
        self.assertEqual(archived.status, "archived")
        self.assertFalse(archived.is_active)
        service.refresh_from_db()
        self.assertIsNone(service.active_workflow_id)

    def test_new_service_catalogue_permissions_are_enforced(self):
        restricted_role = Role.objects.create(
            name="Service Only", permissions={"services": ["list"]}
        )
        restricted_user = User.objects.create_user(
            email="restricted.catalogue@example.com",
            username="restrictedcatalogue",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-CATALOGUE-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }

        response = self.client.get(
            "/api/v1/services/request-field-types", **restricted_headers
        )
        self.assertEqual(response.status_code, 403)

        workflow_response = self.client.get(
            "/api/v1/services/1/workflows", **restricted_headers
        )
        self.assertEqual(workflow_response.status_code, 403)


class ServiceRequestAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_role = Role.objects.create(
            name="Service Request Manager",
            permissions={
                "service_requests": ["create", "view", "list", "update", "delete"],
                "quotes": ["create", "view", "list", "update", "approve"],
                "service_invoices": ["create", "view", "list", "update", "delete"],
                "orders": ["create", "view", "list", "update", "delete"],
                "payments": ["create", "list"],
            },
        )
        self.staff_user = User.objects.create_user(
            email="service.request.staff@example.com",
            username="servicerequeststaff",
            password="password123",
        )
        self.staff_employee = Employee.objects.create(
            user=self.staff_user,
            employee_id="EMP-SR-001",
            role=self.staff_role,
            is_active=True,
        )
        self.staff_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(self.staff_user.id)['access']}"
        }

        self.client_user = User.objects.create_user(
            email="service.request.client@example.com",
            username="servicerequestclient",
            password="password123",
            first_name="Ada",
            last_name="Okoro",
        )
        self.customer = CustomerClient.objects.create(
            user=self.client_user,
            phone="+2348012345678",
            company_name="Ada Holdings",
        )
        self.client_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(self.client_user.id)['access']}"
        }
        self.no_profile_user = User.objects.create_user(
            email="no.client.profile@example.com",
            username="noprofileuser",
            password="password123",
        )
        self.no_profile_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(self.no_profile_user.id)['access']}"
        }

        self.category = ServiceCategory.objects.create(
            name=ServiceCategory.CategoryChoices.SURVEYING,
            description="Surveying services",
        )
        self.branch = self.make_branch("Enugu Commercial", "+2348011111111")
        self.other_branch = self.make_branch("Lagos Commercial", "+2348022222222")
        self.service = Service.objects.create(
            code="SUR-REQ",
            name="Survey Request Service",
            category=self.category,
            division="Land Surveying & Geospatial",
            description="Service request API test service.",
            base_price=Decimal("250000.00"),
            delivery_time="10 days",
            status="active",
            default_sla_days=5,
            fulfillment_mode="managed_case",
            client_visibility="visible",
            created_by=self.staff_user,
        )
        self.subservice = ServiceSubService.objects.create(
            service=self.service,
            code="BOUNDARY",
            name="Boundary Survey",
        )
        self.request_form = ServiceRequestForm.objects.create(
            service=self.service,
            name="Survey Intake",
            version=1,
            status="active",
            is_active=True,
            created_by=self.staff_user,
        )
        ServiceRequestField.objects.create(
            form=self.request_form,
            key="site-location",
            label="Site location",
            field_type="location",
            required=True,
            sort_order=1,
        )
        ServiceRequestField.objects.create(
            form=self.request_form,
            key="plot-size",
            label="Plot size",
            field_type="number",
            required=True,
            sort_order=2,
        )
        ServiceRequestField.objects.create(
            form=self.request_form,
            key="contact-email",
            label="Contact email",
            field_type="email",
            required=True,
            sort_order=3,
        )
        ServiceRequestField.objects.create(
            form=self.request_form,
            key="package",
            label="Package",
            field_type="select",
            required=True,
            options=["standard", "premium"],
            sort_order=4,
        )
        self.pricing_config = ServicePricingConfig.objects.create(
            service=self.service,
            name="Survey Pricing",
            version=1,
            pricing_type="fixed",
            status="active",
            is_active=True,
            created_by=self.staff_user,
        )
        self.workflow = ServiceWorkflow.objects.create(
            service=self.service,
            name="Survey Workflow",
            version=1,
            status="active",
            is_active=True,
            created_by=self.staff_user,
        )
        ServiceWorkflowStage.objects.create(
            workflow=self.workflow,
            name="Request Review",
            sort_order=1,
            client_visible=True,
        )
        ServiceWorkflowStage.objects.create(
            workflow=self.workflow,
            name="Field Survey",
            sort_order=2,
            client_visible=True,
        )
        ServiceWorkflowStage.objects.create(
            workflow=self.workflow,
            name="Quality Review",
            sort_order=3,
            client_visible=False,
        )
        self.service.active_request_form = self.request_form
        self.service.active_pricing_config = self.pricing_config
        self.service.active_workflow = self.workflow
        self.service.save()

    def make_branch(self, name, phone):
        return Branch.objects.create(
            branch_name=name,
            country="Nigeria",
            state="Enugu",
            city="Enugu",
            office_address=f"1 {name} Road",
            contact_email=f"{name.lower().replace(' ', '.')}@example.com",
            contact_phone=phone,
        )

    def request_answers(self, **overrides):
        answers = {
            "site-location": {"address": "Independence Layout, Enugu"},
            "plot-size": "500",
            "contact-email": "client@example.com",
            "package": "standard",
        }
        answers.update(overrides)
        return answers

    def client_payload(self, **overrides):
        payload = {
            "service_id": self.service.id,
            "subservice_id": self.subservice.id,
            "branch_id": self.branch.id,
            "contact_name": "Ada Okoro",
            "contact_phone": "+2348012345678",
            "contact_email": "client@example.com",
            "customer_type": "individual",
            "source": "client_portal",
            "priority": "normal",
            "budget": "700000.00",
            "estimated_value": "650000.00",
            "preferred_date": "2026-08-20",
            "due_date": "2026-08-25",
            "scope_summary": "Boundary survey request.",
            "answers": self.request_answers(),
        }
        payload.update(overrides)
        return payload

    def post_json(self, path, data, headers=None):
        return self.client.post(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **(headers or self.client_headers),
        )

    def patch_json(self, path, data, headers=None):
        return self.client.patch(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **(headers or self.staff_headers),
        )

    def create_client_request(self):
        response = self.post_json("/api/v1/service-requests/", self.client_payload())
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_admin_request(self):
        payload = self.client_payload(
            client_id=self.customer.id,
            source="sales_crm",
            priority="high",
            owner_id=self.staff_employee.id,
        )
        response = self.post_json(
            "/api/v1/service-requests/admin", payload, headers=self.staff_headers
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_request_quote(self, request_id, **overrides):
        payload = {
            "required_approver_role_id": self.staff_role.id,
            "service_fee": "650000.00",
            "other_charges": "50000.00",
            "discount": "25000.00",
            "tax_rate": "7.50",
            "deposit_percent": "30.00",
            "description": "Survey quotation",
            "scope_summary": "Boundary survey request.",
            "terms": "Work begins after mobilisation payment.",
            "valid_until": "2026-08-31",
        }
        payload.update(overrides)
        response = self.post_json(
            f"/api/v1/service-requests/admin/{request_id}/quote",
            payload,
            headers=self.staff_headers,
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_service_order_for_fulfillment(self):
        service_request = self.create_admin_request()
        request_obj = ServiceRequest.objects.get(id=service_request["id"])
        order = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            service_request=request_obj,
            description="Fulfillment order",
            amount=Decimal("650000.00"),
            valid_until=timezone.localdate() + timedelta(days=30),
            due_date=timezone.localdate() + timedelta(days=30),
            created_by=self.staff_user,
            assigned_to=self.staff_employee,
        )
        order.seed_milestones()
        return order

    def test_service_order_model_seeds_workflow_milestones(self):
        order = ServiceOrder.objects.create(
            client=self.customer,
            service=self.service,
            description="Manual survey order",
            amount=Decimal("650000.00"),
            valid_until=timezone.localdate() + timedelta(days=10),
            created_by=self.staff_user,
        )
        order.seed_milestones()

        milestones = list(order.milestones.order_by("sort_order", "id"))
        self.assertEqual(
            [item.name for item in milestones],
            ["Request Review", "Field Survey", "Quality Review"],
        )
        self.assertEqual(milestones[0].status, "active")
        self.assertEqual(milestones[1].status, "pending")
        self.assertEqual(ServiceOrderActivity.objects.count(), 0)

    def test_execution_task_and_deliverable_model_rules(self):
        order = self.create_service_order_for_fulfillment()
        other_order = self.create_service_order_for_fulfillment()
        milestone = order.milestones.first()
        other_milestone = other_order.milestones.first()

        task = ServiceExecutionTask.objects.create(
            order=order,
            milestone=milestone,
            title="Prepare field schedule",
            created_by=self.staff_user,
        )
        self.assertTrue(task.task_number.startswith("TSK-"))
        self.assertEqual(task.status, "to_do")

        with self.assertRaises(ValidationError):
            ServiceExecutionTask.objects.create(
                order=order,
                milestone=other_milestone,
                title="Wrong milestone",
                created_by=self.staff_user,
            )

        with self.assertRaises(ValidationError):
            ServiceDeliverable.objects.create(
                order=order,
                title="Client approval hidden file",
                deliverable_type="report",
                approval_mode="client",
                client_visible=False,
                file_url="https://example.com/hidden.pdf",
                created_by=self.staff_user,
            )

        deliverable = ServiceDeliverable.objects.create(
            order=order,
            task=task,
            title="Survey report",
            deliverable_type="report",
            approval_mode="client",
            client_visible=True,
            status="under_review",
            file_url="https://example.com/report-v1.pdf",
            created_by=self.staff_user,
        )
        deliverable.status = "rejected"
        deliverable.rejected_by = self.client_user
        deliverable.rejected_at = timezone.now()
        deliverable.rejection_reason = "Needs correction."
        deliverable.save()
        deliverable.file_url = "https://example.com/report-v2.pdf"
        with self.assertRaises(ValidationError):
            deliverable.save()

    def test_staff_and_client_execution_task_and_deliverable_endpoints(self):
        order = self.create_service_order_for_fulfillment()
        milestone = order.milestones.first()

        task_response = self.post_json(
            f"/api/v1/orders/{order.id}/tasks",
            {
                "milestone_id": milestone.id,
                "title": "Prepare field schedule",
                "description": "Coordinate field work.",
                "instructions": "Confirm team availability.",
                "acceptance_criteria": "Schedule shared with supervisor.",
                "priority": "high",
                "evidence_required": True,
                "owner_id": self.staff_employee.id,
                "assignee_ids": [self.staff_employee.id],
                "due_date": "2026-09-05",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(task_response.status_code, 201)
        task = task_response.json()
        task_id = task["id"]
        self.assertEqual(task["status"], "to_do")
        self.assertEqual(task["assignee_ids"], [self.staff_employee.id])

        list_tasks = self.client.get(
            f"/api/v1/orders/{order.id}/tasks", **self.staff_headers
        )
        self.assertEqual(list_tasks.status_code, 200)
        self.assertEqual(list_tasks.json()["count"], 1)

        get_task = self.client.get(
            f"/api/v1/orders/{order.id}/tasks/{task_id}", **self.staff_headers
        )
        self.assertEqual(get_task.status_code, 200)
        self.assertEqual(get_task.json()["title"], "Prepare field schedule")

        patch_task = self.patch_json(
            f"/api/v1/orders/{order.id}/tasks/{task_id}",
            {"status": "in_progress", "priority": "critical"},
            headers=self.staff_headers,
        )
        self.assertEqual(patch_task.status_code, 200)
        self.assertEqual(patch_task.json()["status"], "in_progress")

        advance_task = self.post_json(
            f"/api/v1/orders/{order.id}/tasks/{task_id}/advance",
            {},
            headers=self.staff_headers,
        )
        self.assertEqual(advance_task.status_code, 200)
        self.assertEqual(advance_task.json()["status"], "review")

        internal_deliverable_response = self.post_json(
            f"/api/v1/orders/{order.id}/deliverables",
            {
                "milestone_id": milestone.id,
                "task_id": task_id,
                "title": "Internal quality checklist",
                "deliverable_type": "progress_evidence",
                "version": "v1",
                "file_url": "https://example.com/internal-checklist.pdf",
                "file_name": "internal-checklist.pdf",
                "client_visible": False,
                "approval_mode": "supervisor",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(internal_deliverable_response.status_code, 201)
        internal_deliverable = internal_deliverable_response.json()
        self.assertEqual(internal_deliverable["status"], "under_review")

        approve_internal = self.post_json(
            f"/api/v1/orders/{order.id}/deliverables/{internal_deliverable['id']}/approve",
            {},
            headers=self.staff_headers,
        )
        self.assertEqual(approve_internal.status_code, 200)
        self.assertEqual(approve_internal.json()["status"], "approved")

        client_deliverable_response = self.post_json(
            f"/api/v1/orders/{order.id}/deliverables",
            {
                "milestone_id": milestone.id,
                "task_id": task_id,
                "title": "Client survey plan",
                "deliverable_type": "survey_plan",
                "version": "v1",
                "file_url": "https://example.com/survey-plan-v1.pdf",
                "file_name": "survey-plan-v1.pdf",
                "client_visible": True,
                "approval_mode": "client",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(client_deliverable_response.status_code, 201)
        client_deliverable = client_deliverable_response.json()
        self.assertEqual(client_deliverable["status"], "under_review")

        staff_deliverables = self.client.get(
            f"/api/v1/orders/{order.id}/deliverables", **self.staff_headers
        )
        self.assertEqual(staff_deliverables.status_code, 200)
        self.assertEqual(staff_deliverables.json()["count"], 2)

        client_tasks = self.client.get(
            f"/api/v1/service-requests/orders/{order.id}/tasks", **self.client_headers
        )
        self.assertEqual(client_tasks.status_code, 200)
        self.assertEqual(client_tasks.json()["count"], 1)
        self.assertNotIn("instructions", client_tasks.json()["items"][0])

        client_deliverables = self.client.get(
            f"/api/v1/service-requests/orders/{order.id}/deliverables",
            **self.client_headers,
        )
        self.assertEqual(client_deliverables.status_code, 200)
        self.assertEqual(client_deliverables.json()["count"], 1)
        self.assertEqual(
            client_deliverables.json()["items"][0]["id"], client_deliverable["id"]
        )

        hidden_deliverable = self.client.get(
            f"/api/v1/service-requests/orders/{order.id}/deliverables/{internal_deliverable['id']}",
            **self.client_headers,
        )
        self.assertEqual(hidden_deliverable.status_code, 404)

        approve_client = self.post_json(
            f"/api/v1/service-requests/orders/{order.id}/deliverables/{client_deliverable['id']}/approve",
            {},
            headers=self.client_headers,
        )
        self.assertEqual(approve_client.status_code, 200)
        self.assertEqual(approve_client.json()["status"], "approved")

        rejected_deliverable_response = self.post_json(
            f"/api/v1/orders/{order.id}/deliverables",
            {
                "title": "Client report draft",
                "deliverable_type": "report",
                "version": "v1",
                "file_url": "https://example.com/client-report-v1.pdf",
                "client_visible": True,
                "approval_mode": "client",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(rejected_deliverable_response.status_code, 201)
        rejected_deliverable = rejected_deliverable_response.json()
        reject_client = self.post_json(
            f"/api/v1/service-requests/orders/{order.id}/deliverables/{rejected_deliverable['id']}/reject",
            {"reason": "Please revise the report."},
            headers=self.client_headers,
        )
        self.assertEqual(reject_client.status_code, 200)
        self.assertEqual(reject_client.json()["status"], "rejected")

        edit_rejected = self.patch_json(
            f"/api/v1/orders/{order.id}/deliverables/{rejected_deliverable['id']}",
            {"file_url": "https://example.com/client-report-v2.pdf"},
            headers=self.staff_headers,
        )
        self.assertEqual(edit_rejected.status_code, 400)

        order_detail = self.client.get(
            f"/api/v1/orders/{order.id}", **self.staff_headers
        )
        self.assertEqual(order_detail.status_code, 200)
        self.assertEqual(order_detail.json()["task_counts"]["review"], 1)
        self.assertEqual(order_detail.json()["deliverable_counts"]["approved"], 2)
        self.assertEqual(order_detail.json()["deliverable_counts"]["rejected"], 1)

    def test_metadata_endpoints_return_choices_and_active_intake_form(self):
        choices_response = self.client.get(
            "/api/v1/service-requests/choices", **self.client_headers
        )
        self.assertEqual(choices_response.status_code, 200)
        self.assertIn("statuses", choices_response.json())
        self.assertIn("field_types", choices_response.json())

        form_response = self.client.get(
            f"/api/v1/service-requests/services/{self.service.id}/intake-form",
            **self.client_headers,
        )
        self.assertEqual(form_response.status_code, 200)
        data = form_response.json()
        self.assertEqual(data["service"]["id"], self.service.id)
        self.assertEqual(data["active_request_form"]["id"], self.request_form.id)
        self.assertEqual(len(data["active_request_form"]["fields"]), 4)

    def test_client_can_create_list_detail_and_summary(self):
        created = self.create_client_request()
        self.assertEqual(created["service_id"], self.service.id)
        self.assertEqual(created["status"], "new")
        self.assertEqual(created["request_form_version"], 1)
        self.assertEqual(len(created["answers"]), 4)
        self.assertEqual(len(created["activities"]), 1)

        list_response = self.client.get(
            "/api/v1/service-requests/", **self.client_headers
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)
        self.assertEqual(
            list_response.json()["items"][0]["request_number"],
            created["request_number"],
        )

        detail_response = self.client.get(
            f"/api/v1/service-requests/{created['id']}", **self.client_headers
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["answers_snapshot"]["plot-size"], "500")

        summary_response = self.client.get(
            "/api/v1/service-requests/summary", **self.client_headers
        )
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["new"], 1)
        self.assertEqual(summary_response.json()["total"], 1)

    def test_client_submission_requires_client_profile_and_valid_answers(self):
        missing_profile = self.post_json(
            "/api/v1/service-requests/",
            self.client_payload(),
            headers=self.no_profile_headers,
        )
        self.assertEqual(missing_profile.status_code, 400)

        payload = self.client_payload(answers=self.request_answers(package="invalid"))
        invalid_response = self.post_json("/api/v1/service-requests/", payload)
        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn("package", invalid_response.json()["detail"])

    def test_staff_can_create_filter_update_activity_attachment_and_quote(self):
        payload = self.client_payload(
            client_id=self.customer.id,
            source="sales_crm",
            priority="high",
            owner_id=self.staff_employee.id,
        )
        response = self.post_json(
            "/api/v1/service-requests/admin", payload, headers=self.staff_headers
        )
        self.assertEqual(response.status_code, 201)
        request_id = response.json()["id"]
        self.assertEqual(response.json()["owner_id"], self.staff_employee.id)

        list_response = self.client.get(
            f"/api/v1/service-requests/admin?priority=high&search={response.json()['request_number']}",
            **self.staff_headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        patch_response = self.patch_json(
            f"/api/v1/service-requests/admin/{request_id}",
            {"status": "under_review", "next_action": "Call client"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["status"], "under_review")
        self.assertEqual(
            patch_response.json()["activities"][0]["activity_type"], "status_change"
        )

        activity_response = self.post_json(
            f"/api/v1/service-requests/admin/{request_id}/activities",
            {
                "activity_type": "phone_call",
                "outcome": "successful",
                "note": "Client reached.",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(activity_response.status_code, 201)
        self.assertEqual(activity_response.json()["activity_type"], "phone_call")

        attachment_response = self.post_json(
            f"/api/v1/service-requests/admin/{request_id}/attachments",
            {
                "field_key": "site-location",
                "label": "Site photo",
                "file_name": "site.jpg",
                "file_url": "https://example.com/site.jpg",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(attachment_response.status_code, 201)

        quote_response = self.post_json(
            f"/api/v1/service-requests/admin/{request_id}/quote",
            {
                "amount": "650000.00",
                "description": "Survey quotation",
                "required_approver_role_id": self.staff_role.id,
            },
            headers=self.staff_headers,
        )
        self.assertEqual(quote_response.status_code, 201)
        self.assertEqual(quote_response.json()["status"], "under_review")
        self.assertTrue(quote_response.json()["quote_number"].startswith("QTE-"))
        quote_detail = self.client.get(
            f"/api/v1/quotes/{quote_response.json()['quote_id']}", **self.staff_headers
        )
        self.assertEqual(quote_detail.status_code, 200)
        self.assertEqual(
            quote_detail.json()["required_approver_role_id"], self.staff_role.id
        )
        self.assertEqual(
            quote_detail.json()["required_approver_role_name"], self.staff_role.name
        )

    def test_service_request_quote_requires_approver_role(self):
        service_request = self.create_admin_request()
        response = self.post_json(
            f"/api/v1/service-requests/admin/{service_request['id']}/quote",
            {"amount": "650000.00", "description": "Survey quotation"},
            headers=self.staff_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("required_approver_role_id", response.json()["detail"])

    @patch("domains.service_operations.api.v1.routers.quotes.send_mail")
    def test_quote_approval_sends_to_client_and_client_can_accept(self, send_mail_mock):
        service_request = self.create_admin_request()
        quoted_request = self.create_request_quote(service_request["id"])
        quote_id = quoted_request["quote_id"]

        hidden_response = self.client.get(
            "/api/v1/service-requests/quotes", **self.client_headers
        )
        self.assertEqual(hidden_response.status_code, 200)
        self.assertEqual(hidden_response.json()["count"], 0)

        approve_response = self.post_json(
            f"/api/v1/quotes/{quote_id}/approve",
            {},
            headers=self.staff_headers,
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "sent")
        self.assertEqual(approve_response.json()["approved_by_id"], self.staff_user.id)
        self.assertEqual(approve_response.json()["deposit_amount"], "217687.50")
        send_mail_mock.assert_called_once()

        visible_response = self.client.get(
            "/api/v1/service-requests/quotes", **self.client_headers
        )
        self.assertEqual(visible_response.status_code, 200)
        self.assertEqual(visible_response.json()["count"], 1)
        self.assertEqual(visible_response.json()["items"][0]["id"], quote_id)

        accept_response = self.post_json(
            f"/api/v1/service-requests/quotes/{quote_id}/accept",
            {},
            headers=self.client_headers,
        )
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.json()["status"], "accepted")

        follow_up = self.client.get(
            f"/api/v1/service-requests/admin/{service_request['id']}",
            **self.staff_headers,
        )
        self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(
            follow_up.json()["next_action"], "Create invoice for accepted quotation"
        )
        self.assertEqual(
            follow_up.json()["activities"][0]["activity_type"], "quote_accepted"
        )

    def test_quote_approval_requires_permission(self):
        service_request = self.create_admin_request()
        no_approval_role = Role.objects.create(
            name="Quote Creator Without Approval",
            permissions={
                "quotes": ["create", "view", "list"],
                "service_requests": ["list", "view"],
            },
        )
        quoted_request = self.create_request_quote(
            service_request["id"],
            required_approver_role_id=no_approval_role.id,
        )
        quote_id = quoted_request["quote_id"]

        no_approval_user = User.objects.create_user(
            email="quote.no.approval@example.com",
            username="quotenoapproval",
            password="password123",
        )
        Employee.objects.create(
            user=no_approval_user,
            employee_id="EMP-NO-QUOTE-APPROVAL",
            role=no_approval_role,
            is_active=True,
        )
        no_approval_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(no_approval_user.id)['access']}"
        }

        response = self.post_json(
            f"/api/v1/quotes/{quote_id}/approve", {}, headers=no_approval_headers
        )
        self.assertEqual(response.status_code, 403)

    def test_quote_approval_requires_matching_role(self):
        service_request = self.create_admin_request()
        quoted_request = self.create_request_quote(service_request["id"])
        quote_id = quoted_request["quote_id"]

        other_role = Role.objects.create(
            name="Other Quote Approver",
            permissions={"quotes": ["approve", "view", "list"]},
        )
        other_user = User.objects.create_user(
            email="quote.wrong.role@example.com",
            username="quotewrongrole",
            password="password123",
        )
        Employee.objects.create(
            user=other_user,
            employee_id="EMP-WRONG-QUOTE-ROLE",
            role=other_role,
            is_active=True,
        )
        other_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(other_user.id)['access']}"
        }

        response = self.post_json(
            f"/api/v1/quotes/{quote_id}/approve", {}, headers=other_headers
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("different role", response.json()["detail"])

    @patch("domains.service_operations.api.v1.routers.quotes.send_mail")
    def test_rejected_quote_is_immutable_and_replacement_links_revision(
        self, send_mail_mock
    ):
        service_request = self.create_admin_request()
        quoted_request = self.create_request_quote(service_request["id"])
        quote_id = quoted_request["quote_id"]

        approve_response = self.post_json(
            f"/api/v1/quotes/{quote_id}/approve", {}, headers=self.staff_headers
        )
        self.assertEqual(approve_response.status_code, 200)

        reject_response = self.post_json(
            f"/api/v1/service-requests/quotes/{quote_id}/reject",
            {"reason": "Please revise scope."},
            headers=self.client_headers,
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["status"], "rejected")
        self.assertEqual(
            reject_response.json()["client_rejection_reason"], "Please revise scope."
        )

        edit_rejected = self.patch_json(
            f"/api/v1/quotes/{quote_id}",
            {"service_fee": "700000.00"},
            headers=self.staff_headers,
        )
        self.assertEqual(edit_rejected.status_code, 400)

        replacement = self.create_request_quote(
            service_request["id"], service_fee="700000.00"
        )
        replacement_quote_id = replacement["quote_id"]
        replacement_detail = self.client.get(
            f"/api/v1/quotes/{replacement_quote_id}", **self.staff_headers
        )
        self.assertEqual(replacement_detail.status_code, 200)
        self.assertEqual(replacement_detail.json()["previous_quote_id"], quote_id)
        self.assertEqual(replacement_detail.json()["version"], 2)

    @patch("domains.service_operations.api.v1.routers.invoices.send_mail")
    @patch("domains.service_operations.api.v1.routers.quotes.send_mail")
    def test_invoice_and_payment_flow_from_accepted_quote(
        self, quote_send_mail_mock, invoice_send_mail_mock
    ):
        service_request = self.create_admin_request()
        quoted_request = self.create_request_quote(service_request["id"])
        quote_id = quoted_request["quote_id"]

        draft_invoice_response = self.post_json(
            f"/api/v1/quotes/{quote_id}/invoice",
            {"due_date": "2026-09-10"},
            headers=self.staff_headers,
        )
        self.assertEqual(draft_invoice_response.status_code, 400)

        approve_response = self.post_json(
            f"/api/v1/quotes/{quote_id}/approve", {}, headers=self.staff_headers
        )
        self.assertEqual(approve_response.status_code, 200)
        accept_response = self.post_json(
            f"/api/v1/service-requests/quotes/{quote_id}/accept",
            {},
            headers=self.client_headers,
        )
        self.assertEqual(accept_response.status_code, 200)

        invoice_response = self.post_json(
            f"/api/v1/quotes/{quote_id}/invoice",
            {
                "due_date": "2026-09-10",
                "payment_schedule": "30% mobilisation",
                "payment_instructions": "Transfer to Bomach account.",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(invoice_response.status_code, 201)
        invoice = invoice_response.json()
        invoice_id = invoice["id"]
        self.assertEqual(invoice["quote_id"], quote_id)
        self.assertEqual(invoice["service_request_id"], service_request["id"])
        self.assertEqual(invoice["status"], "draft")
        self.assertEqual(invoice["activation_threshold_amount"], "217687.50")

        duplicate_response = self.post_json(
            f"/api/v1/quotes/{quote_id}/invoice",
            {"due_date": "2026-09-10"},
            headers=self.staff_headers,
        )
        self.assertEqual(duplicate_response.status_code, 400)

        hidden_invoices = self.client.get(
            "/api/v1/service-requests/invoices", **self.client_headers
        )
        self.assertEqual(hidden_invoices.status_code, 200)
        self.assertEqual(hidden_invoices.json()["count"], 0)

        send_response = self.post_json(
            f"/api/v1/invoices/{invoice_id}/send",
            {"payment_instructions": "Transfer to Bomach account."},
            headers=self.staff_headers,
        )
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(send_response.json()["status"], "sent")
        invoice_send_mail_mock.assert_called_once()

        visible_invoices = self.client.get(
            "/api/v1/service-requests/invoices", **self.client_headers
        )
        self.assertEqual(visible_invoices.status_code, 200)
        self.assertEqual(visible_invoices.json()["count"], 1)
        self.assertEqual(visible_invoices.json()["items"][0]["id"], invoice_id)

        early_order_response = self.post_json(
            f"/api/v1/invoices/{invoice_id}/service-order",
            {"assigned_to_id": self.staff_employee.id, "due_date": "2026-09-20"},
            headers=self.staff_headers,
        )
        self.assertEqual(early_order_response.status_code, 400)
        self.assertIn("Payment threshold", early_order_response.json()["detail"])

        submission_response = self.post_json(
            f"/api/v1/service-requests/invoices/{invoice_id}/payment-submissions",
            {
                "invoice_id": invoice_id,
                "amount": "217687.50",
                "payment_method": "bank_transfer",
                "payment_date": "2026-08-05",
                "proof_of_payment": "https://example.com/proof.png",
                "notes": "Mobilisation payment",
            },
            headers=self.client_headers,
        )
        self.assertEqual(submission_response.status_code, 201)
        submission_id = submission_response.json()["id"]

        pending_response = self.client.get(
            "/api/v1/invoices/payment-submissions", **self.staff_headers
        )
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.json()["count"], 1)
        finance_account = FinanceAccount.objects.create(
            account_type=FinanceAccount.ACCOUNT_TYPE.BANK,
            display_name="GTBank Service Collections",
            branch=self.branch,
            bank_name="GTBank",
            account_number="0123456789",
            account_name="Bomach Group",
            created_by=self.staff_user,
        )

        review_response = self.post_json(
            f"/api/v1/invoices/payment-submissions/{submission_id}/review",
            {
                "status": "confirmed",
                "finance_account_id": finance_account.id,
                "rejection_reason": "",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["status"], "Confirmed")

        invoice_detail = self.client.get(
            f"/api/v1/invoices/{invoice_id}", **self.staff_headers
        )
        self.assertEqual(invoice_detail.status_code, 200)
        self.assertEqual(invoice_detail.json()["amount_paid"], "217687.50")
        self.assertEqual(invoice_detail.json()["status"], "partially_paid")
        self.assertIsNotNone(invoice_detail.json()["activation_threshold_met_at"])

        order_response = self.post_json(
            f"/api/v1/invoices/{invoice_id}/service-order",
            {
                "assigned_to_id": self.staff_employee.id,
                "due_date": "2026-09-20",
                "description": "Mobilised survey order",
            },
            headers=self.staff_headers,
        )
        self.assertEqual(order_response.status_code, 201)
        order = order_response.json()
        order_id = order["id"]
        self.assertEqual(order["invoice_id"], invoice_id)
        self.assertEqual(order["service_request_id"], service_request["id"])
        self.assertEqual(order["order_status"], "pending_mobilisation")
        self.assertEqual(order["assigned_to_id"], self.staff_employee.id)
        self.assertEqual(len(order["milestones"]), 3)
        self.assertEqual(order["milestones"][0]["status"], "active")

        duplicate_order_response = self.post_json(
            f"/api/v1/invoices/{invoice_id}/service-order",
            {"assigned_to_id": self.staff_employee.id},
            headers=self.staff_headers,
        )
        self.assertEqual(duplicate_order_response.status_code, 400)

        complete_response = self.post_json(
            f"/api/v1/orders/{order_id}/milestones/{order['milestones'][0]['id']}/complete",
            {},
            headers=self.staff_headers,
        )
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.json()["order_status"], "active")
        self.assertEqual(complete_response.json()["progress"], 33)

        client_orders = self.client.get(
            "/api/v1/service-requests/orders", **self.client_headers
        )
        self.assertEqual(client_orders.status_code, 200)
        self.assertEqual(client_orders.json()["count"], 1)
        self.assertEqual(client_orders.json()["items"][0]["id"], order_id)
        self.assertEqual(len(client_orders.json()["items"][0]["milestones"]), 2)

        client_order_detail = self.client.get(
            f"/api/v1/service-requests/orders/{order_id}", **self.client_headers
        )
        self.assertEqual(client_order_detail.status_code, 200)
        self.assertEqual(client_order_detail.json()["invoice_id"], invoice_id)

        follow_up = self.client.get(
            f"/api/v1/service-requests/admin/{service_request['id']}",
            **self.staff_headers,
        )
        self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(follow_up.json()["status"], "converted")
        self.assertIn(order["order_number"], follow_up.json()["next_action"])

    def test_client_activity_and_attachment_are_limited_to_own_request(self):
        created = self.create_client_request()
        activity_response = self.post_json(
            f"/api/v1/service-requests/{created['id']}/activities",
            {"activity_type": "document_received", "note": "Uploaded title document."},
        )
        self.assertEqual(activity_response.status_code, 201)

        restricted_response = self.post_json(
            f"/api/v1/service-requests/{created['id']}/activities",
            {"activity_type": "phone_call", "note": "Not allowed."},
        )
        self.assertEqual(restricted_response.status_code, 400)

        attachment_response = self.post_json(
            f"/api/v1/service-requests/{created['id']}/attachments",
            {
                "field_key": "site-location",
                "label": "Title document",
                "file_name": "title.pdf",
                "file_url": "https://example.com/title.pdf",
            },
        )
        self.assertEqual(attachment_response.status_code, 201)

    def test_staff_permissions_and_branch_scope_are_enforced(self):
        other_request = ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            branch=self.other_branch,
            contact_name="Ada Okoro",
            contact_email="client@example.com",
            answers_snapshot=self.request_answers(),
            created_by=self.staff_user,
        )
        ServiceRequest.objects.create(
            client=self.customer,
            service=self.service,
            branch=self.branch,
            contact_name="Ada Okoro",
            contact_email="client@example.com",
            answers_snapshot=self.request_answers(),
            created_by=self.staff_user,
        )
        scoped_role = Role.objects.create(
            name="Scoped Service Request Manager",
            permissions={"service_requests": ["list", "view"]},
        )
        scoped_role.branches.add(self.branch)
        scoped_user = User.objects.create_user(
            email="scoped.service.request@example.com",
            username="scopedservicerequest",
            password="password123",
        )
        Employee.objects.create(
            user=scoped_user,
            employee_id="EMP-SR-SCOPED",
            role=scoped_role,
            branch=self.branch,
            is_active=True,
        )
        scoped_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(scoped_user.id)['access']}"
        }

        list_response = self.client.get(
            "/api/v1/service-requests/admin", **scoped_headers
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)
        self.assertEqual(list_response.json()["items"][0]["branch_id"], self.branch.id)

        detail_response = self.client.get(
            f"/api/v1/service-requests/admin/{other_request.id}", **scoped_headers
        )
        self.assertEqual(detail_response.status_code, 403)

        no_permission_role = Role.objects.create(
            name="No Service Request Access", permissions={"services": ["list"]}
        )
        no_permission_user = User.objects.create_user(
            email="no.service.request.permission@example.com",
            username="noservicerequestpermission",
            password="password123",
        )
        Employee.objects.create(
            user=no_permission_user,
            employee_id="EMP-SR-NO-PERM",
            role=no_permission_role,
            is_active=True,
        )
        denied_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(no_permission_user.id)['access']}"
        }
        denied_response = self.client.get(
            "/api/v1/service-requests/admin", **denied_headers
        )
        self.assertEqual(denied_response.status_code, 403)


class LeadModelTests(TestCase):
    def test_priority_sla_and_stale_properties(self):
        lead = Lead.objects.create(
            full_name="Adaeze Chukwu",
            phone="08012345678",
            division="real_estate",
            source="facebook_ad",
            score=82,
        )

        Lead.objects.filter(id=lead.id).update(
            created_at=timezone.now() - timedelta(minutes=31)
        )
        lead.refresh_from_db()

        self.assertEqual(lead.priority, "hot")
        self.assertTrue(lead.is_sla_breached)
        self.assertFalse(lead.is_stale)

        Lead.objects.filter(id=lead.id).update(
            created_at=timezone.now() - timedelta(days=13)
        )
        lead.refresh_from_db()

        self.assertTrue(lead.is_stale)
        self.assertEqual(str(lead), "Adaeze Chukwu - New")

    def test_lead_activity_sequences_are_per_lead(self):
        first_lead = Lead.objects.create(
            full_name="Adaeze Chukwu",
            phone="08012345678",
            division="real_estate",
            source="facebook_ad",
        )
        second_lead = Lead.objects.create(
            full_name="Bello Kabiru",
            phone="08031239876",
            division="engineering",
            source="referral",
        )

        first_activity = LeadActivity.create_for_lead(
            first_lead.id,
            activity_type="phone_call",
            outcome="connected",
            note="First call completed.",
        )
        second_activity = LeadActivity.create_for_lead(
            first_lead.id,
            activity_type="whatsapp",
            outcome="interested",
            note="Sent property details.",
        )
        other_lead_activity = LeadActivity.create_for_lead(
            second_lead.id,
            activity_type="email",
            outcome="needs_follow_up",
            note="Sent requirements.",
        )

        self.assertEqual(first_activity.sequence, 1)
        self.assertEqual(second_activity.sequence, 2)
        self.assertEqual(other_lead_activity.sequence, 1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LeadActivity.objects.create(
                    lead=first_lead,
                    sequence=1,
                    activity_type="meeting",
                    outcome="connected",
                    note="Duplicate sequence.",
                )


class MarketingLeadAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.role = Role.objects.create(
            name="Marketing Lead Manager",
            permissions={
                "leads": ["create", "view", "list", "update", "delete"],
                "marketing_campaigns": ["create", "view", "list", "update", "delete"],
                "marketing_dashboard": ["view"],
                "content": ["create", "view", "list", "update", "delete"],
                "revenue_execution": [
                    "create",
                    "view",
                    "list",
                    "update",
                    "delete",
                    "complete",
                ],
                "service_leads": ["list"],
                "meetings": ["create", "view", "list", "update", "delete"],
            },
        )
        self.user = User.objects.create_user(
            email="lead.manager@example.com",
            username="leadmanager",
            password="password123",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id="EMP-LEADS-001",
            role=self.role,
            is_active=True,
        )
        token = JWTService.create_tokens(self.user.id)["access"]
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def post_json(self, path, data):
        return self.client.post(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **self.headers,
        )

    def patch_json(self, path, data):
        return self.client.patch(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **self.headers,
        )

    def put_json(self, path, data):
        return self.client.put(
            path,
            data=json.dumps(data),
            content_type="application/json",
            **self.headers,
        )

    def create_lead(self, **overrides):
        payload = {
            "full_name": "Bello Kabiru",
            "phone": "08031239876",
            "email": "bello@example.com",
            "division": "real_estate",
            "source": "facebook_ad",
            "budget_range": "NGN 5M",
            "estimated_value": "5000000.00",
            "notes": "Interested in Bethel City Estate",
            "tags": ["estate"],
            "score": 84,
            "next_action": "Call and qualify",
        }
        payload.update(overrides)
        return self.post_json("/api/v1/leads", payload)

    def create_campaign(self, **overrides):
        payload = {
            "name": "Bethel City Estate Launch",
            "description": "Estate launch and inspection campaign.",
            "status": "active",
            "channel": "social_media",
            "impressions": 10000,
            "ctr": "4.00",
            "roi": "0.00",
            "budget_allocated": "1000000.00",
            "budget_spent": "250000.00",
            "start_date": timezone.localdate().isoformat(),
            "end_date": (timezone.localdate() + timedelta(days=10)).isoformat(),
        }
        payload.update(overrides)
        return self.post_json("/api/v1/marketing-campaigns", payload)

    def create_activity(self, lead_id, **overrides):
        payload = {
            "activity_type": "phone_call",
            "outcome": "connected",
            "note": "Discussed budget, timeline and inspection preference.",
            "next_follow_up_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "next_action": "Send payment plan and call by 10 AM",
            "to_status": "contacted",
        }
        payload.update(overrides)
        return self.post_json(f"/api/v1/leads/{lead_id}/activities", payload)

    def create_daily_template(self, **overrides):
        payload = {
            "title": "Contact every new and overdue lead",
            "description": "CSRC and sales must clear all new, uncontacted, and breached leads.",
            "default_owner_id": self.employee.id,
            "severity": "critical",
            "is_active": True,
            "sort_order": 1,
        }
        payload.update(overrides)
        return self.post_json("/api/v1/revenue-execution/action-templates", payload)

    def create_turnaround_plan(self, **overrides):
        payload = {
            "name": "Q3 Marketing and Sales Turnaround",
            "start_date": timezone.localdate().isoformat(),
            "primary_owner_id": self.employee.id,
        }
        payload.update(overrides)
        return self.post_json("/api/v1/revenue-execution/turnaround/plans", payload)

    def create_revenue_target(
        self, target_value="10000000.00", progress_value="2500000.00"
    ):
        today = timezone.localdate()
        template = RoleTargetTemplate.objects.create(
            role=self.role,
            title="Revenue closed",
            target_value=target_value,
            unit="NGN",
            period="monthly",
            sequence=1,
        )
        target = EmployeeTarget.objects.create(
            employee=self.employee,
            role=self.role,
            role_target_template=template,
            title=template.title,
            target_value=template.target_value,
            unit=template.unit,
            period=template.period,
            period_start=today.replace(day=1),
            period_end=today,
            sequence=1,
        )
        EmployeeTargetReport.objects.create(
            employee_target=target,
            summary="Revenue booked and verified.",
            progress_value=progress_value,
            status=EmployeeTargetReport.Status.APPROVED,
            reviewed_by=self.user,
            reviewed_at=timezone.now(),
        )
        return target

    def test_create_list_filter_retrieve_update_and_summary(self):
        create_response = self.create_lead(
            status="negotiation",
            source="referral",
            estimated_value="12000000.00",
        )
        self.assertEqual(create_response.status_code, 201)
        lead_id = create_response.json()["id"]

        list_response = self.client.get(
            "/api/v1/leads?division=real_estate&priority=hot&search=Bello",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        detail_response = self.client.get(f"/api/v1/leads/{lead_id}", **self.headers)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["priority"], "hot")

        update_response = self.patch_json(
            f"/api/v1/leads/{lead_id}",
            {"status": "qualified", "score": 91},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["status"], "qualified")
        self.assertIsNotNone(update_response.json()["first_contact_at"])

        summary_response = self.client.get("/api/v1/leads/summary", **self.headers)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["total"], 1)
        self.assertEqual(summary_response.json()["hot_leads"], 1)

    def test_assign_status_delete_and_service_lead_route_split(self):
        create_response = self.create_lead(score=40)
        lead_id = create_response.json()["id"]

        assign_response = self.patch_json(
            f"/api/v1/leads/{lead_id}/assign",
            {"assigned_to_id": self.employee.id},
        )
        self.assertEqual(assign_response.status_code, 200)
        self.assertEqual(assign_response.json()["assigned_to_id"], self.employee.id)

        status_response = self.patch_json(
            f"/api/v1/leads/{lead_id}/status",
            {"status": "contacted"},
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "contacted")
        self.assertIsNotNone(status_response.json()["last_contact_at"])

        service_leads_response = self.client.get(
            "/api/v1/service-leads", **self.headers
        )
        self.assertEqual(service_leads_response.status_code, 200)

        delete_response = self.client.delete(f"/api/v1/leads/{lead_id}", **self.headers)
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Lead.objects.filter(id=lead_id).exists())

    def test_create_list_retrieve_patch_and_delete_lead_activities(self):
        lead_response = self.create_lead(score=55)
        lead_id = lead_response.json()["id"]

        activity_response = self.create_activity(lead_id)
        self.assertEqual(activity_response.status_code, 201)
        activity = activity_response.json()
        self.assertEqual(activity["sequence"], 1)
        self.assertEqual(activity["from_status"], "new")
        self.assertEqual(activity["to_status"], "contacted")

        lead = Lead.objects.get(id=lead_id)
        self.assertEqual(lead.status, "contacted")
        self.assertEqual(lead.next_action, "Send payment plan and call by 10 AM")
        self.assertIsNotNone(lead.first_contact_at)
        self.assertIsNotNone(lead.last_contact_at)

        second_activity_response = self.create_activity(
            lead_id,
            activity_type="whatsapp",
            outcome="interested",
            note="Shared estate brochure.",
            to_status="qualified",
        )
        self.assertEqual(second_activity_response.status_code, 201)
        self.assertEqual(second_activity_response.json()["sequence"], 2)

        other_lead_response = self.create_lead(
            full_name="Ada Nwoji", phone="07031230000"
        )
        other_activity_response = self.create_activity(other_lead_response.json()["id"])
        self.assertEqual(other_activity_response.status_code, 201)
        self.assertEqual(other_activity_response.json()["sequence"], 1)

        list_response = self.client.get(
            f"/api/v1/leads/{lead_id}/activities?activity_type=phone_call",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

        activity_id = activity["id"]
        detail_response = self.client.get(
            f"/api/v1/leads/{lead_id}/activities/{activity_id}",
            **self.headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], activity_id)

        patch_response = self.patch_json(
            f"/api/v1/leads/{lead_id}/activities/{activity_id}",
            {"note": "Updated call summary.", "outcome": "needs_follow_up"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["note"], "Updated call summary.")
        self.assertEqual(patch_response.json()["outcome"], "needs_follow_up")

        wrong_parent_response = self.client.get(
            f"/api/v1/leads/{other_lead_response.json()['id']}/activities/{activity_id}",
            **self.headers,
        )
        self.assertEqual(wrong_parent_response.status_code, 404)

        delete_response = self.client.delete(
            f"/api/v1/leads/{lead_id}/activities/{activity_id}",
            **self.headers,
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(LeadActivity.objects.filter(id=activity_id).exists())

    def test_lead_journal_uses_canonical_choice_values(self):
        lead_response = self.create_lead(status="qualified")
        lead_id = lead_response.json()["id"]

        activity_response = self.create_activity(
            lead_id,
            activity_type="phone_call",
            outcome="connected",
            to_status="proposal_sent",
        )
        self.assertEqual(activity_response.status_code, 201)
        activity = activity_response.json()
        self.assertEqual(activity["activity_type"], "phone_call")
        self.assertEqual(activity["outcome"], "connected")
        self.assertEqual(activity["from_status"], "qualified")
        self.assertEqual(activity["to_status"], "proposal_sent")

        lead = Lead.objects.get(id=lead_id)
        self.assertEqual(lead.status, "proposal_sent")

        list_response = self.client.get(
            f"/api/v1/leads/{lead_id}/activities?activity_type=phone_call&outcome=connected",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)

    def test_pipeline_board_filters_summary_columns_and_detail(self):
        branch = Branch.objects.create(
            branch_name="Pipeline Test Branch",
            branch_id="PIPE-001",
            country="Nigeria",
            state="Enugu",
            office_address="1 Pipeline Road",
            contact_email="pipeline.branch@example.com",
            contact_phone="08030009999",
        )
        self.employee.branch = branch
        self.employee.save(update_fields=["branch", "updated_at"])

        new_response = self.create_lead(
            full_name="Pipeline New Lead",
            phone="08030001001",
            status="new",
            division="real_estate",
            estimated_value="5000000.00",
            assigned_to_id=self.employee.id,
            branch_id=branch.id,
        )
        proposal_response = self.create_lead(
            full_name="Pipeline Proposal Lead",
            phone="08030001002",
            status="proposal_sent",
            division="engineering",
            estimated_value="10000000.00",
            assigned_to_id=self.employee.id,
            branch_id=branch.id,
            next_follow_up_at=timezone.now().isoformat(),
            next_action="Review proposal",
        )
        won_response = self.create_lead(
            full_name="Pipeline Won Lead",
            phone="08030001003",
            status="won",
            division="real_estate",
            estimated_value="20000000.00",
            assigned_to_id=self.employee.id,
            branch_id=branch.id,
        )
        lost_response = self.create_lead(
            full_name="Pipeline Lost Lead",
            phone="08030001004",
            status="lost",
            division="benji",
            estimated_value="15000000.00",
            branch_id=branch.id,
        )
        self.assertEqual(new_response.status_code, 201)
        self.assertEqual(proposal_response.status_code, 201)
        self.assertEqual(won_response.status_code, 201)
        self.assertEqual(lost_response.status_code, 201)

        new_id = new_response.json()["id"]
        proposal_id = proposal_response.json()["id"]
        Lead.objects.filter(id=new_id).update(
            first_response_due_at=timezone.now() - timedelta(minutes=5),
            first_response_at=None,
            first_contact_at=None,
            sla_status="breached",
        )
        activity_response = self.create_activity(
            proposal_id,
            activity_type="email",
            outcome="needs_follow_up",
            note="Proposal sent and awaiting customer response.",
            to_status="proposal_sent",
        )
        self.assertEqual(activity_response.status_code, 201)

        response = self.client.get(
            f"/api/v1/leads/pipeline?branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"]["total_leads"], 4)
        self.assertEqual(data["summary"]["overdue_count"], 1)
        self.assertEqual(data["summary"]["sla_breach_count"], 1)
        self.assertEqual(data["summary"]["active_pipeline_value"], "15000000.00")
        self.assertEqual(data["summary"]["won_count"], 1)
        self.assertEqual(data["summary"]["conversion_rate"], 25.0)
        self.assertEqual(
            [column["status"] for column in data["columns"]],
            [
                "new",
                "contacted",
                "qualified",
                "proposal_sent",
                "negotiation",
                "won",
                "lost",
            ],
        )
        columns = {column["status"]: column for column in data["columns"]}
        self.assertEqual(columns["contacted"]["count"], 0)
        self.assertEqual(columns["new"]["count"], 1)
        self.assertEqual(columns["new"]["cards"][0]["id"], new_id)
        self.assertTrue(columns["new"]["cards"][0]["is_sla_breached"])
        self.assertEqual(
            columns["proposal_sent"]["total_estimated_value"], "10000000.00"
        )

        division_response = self.client.get(
            f"/api/v1/leads/pipeline?branch_id={branch.id}&division=real_estate",
            **self.headers,
        )
        self.assertEqual(division_response.status_code, 200)
        self.assertEqual(division_response.json()["summary"]["total_leads"], 2)

        owner_response = self.client.get(
            f"/api/v1/leads/pipeline?branch_id={branch.id}&assigned_to_id={self.employee.id}&search=Proposal",
            **self.headers,
        )
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response.json()["summary"]["total_leads"], 1)
        self.assertEqual(
            owner_response.json()["columns"][3]["cards"][0]["id"], proposal_id
        )

        detail_response = self.client.get(
            f"/api/v1/leads/pipeline/{proposal_id}",
            **self.headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(detail["lead"]["id"], proposal_id)
        self.assertEqual(detail["lead"]["status"], "proposal_sent")
        self.assertEqual(detail["lead"]["assigned_to_id"], self.employee.id)
        self.assertEqual(len(detail["activity_timeline"]), 1)
        self.assertEqual(detail["activity_timeline"][0]["activity_type"], "email")

    def test_pipeline_requires_lead_permissions(self):
        lead_response = self.create_lead(status="new")
        self.assertEqual(lead_response.status_code, 201)
        restricted_role = Role.objects.create(
            name="Pipeline Restricted User",
            permissions={"leads": ["view"]},
        )
        restricted_user = User.objects.create_user(
            email="pipeline.restricted@example.com",
            username="pipelinerestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-PIPE-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }

        board_response = self.client.get("/api/v1/leads/pipeline", **restricted_headers)
        self.assertEqual(board_response.status_code, 403)

        detail_response = self.client.get(
            f"/api/v1/leads/pipeline/{lead_response.json()['id']}",
            **restricted_headers,
        )
        self.assertEqual(detail_response.status_code, 200)

    def test_campaign_panel_and_workspace_core_flow(self):
        branch = Branch.objects.create(
            branch_name="Campaign Test Branch",
            branch_id="CAMP-001",
            country="Nigeria",
            state="Enugu",
            office_address="1 Campaign Road",
            contact_email="campaign.branch@example.com",
            contact_phone="08030008888",
        )
        self.employee.branch = branch
        self.employee.save(update_fields=["branch", "updated_at"])

        campaign_response = self.create_campaign()
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]

        qualified_response = self.create_lead(
            full_name="Campaign Qualified Lead",
            phone="08030002001",
            status="qualified",
            estimated_value="6000000.00",
            campaign_id=campaign_id,
            branch_id=branch.id,
        )
        won_response = self.create_lead(
            full_name="Campaign Won Lead",
            phone="08030002002",
            status="won",
            estimated_value="4000000.00",
            campaign_id=campaign_id,
            branch_id=branch.id,
        )
        self.assertEqual(qualified_response.status_code, 201)
        self.assertEqual(won_response.status_code, 201)

        panel_response = self.client.get(
            f"/api/v1/marketing-campaigns/panel?branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(panel_response.status_code, 200)
        panel = panel_response.json()
        self.assertEqual(panel["kpis"]["total_campaigns"], 1)
        self.assertEqual(panel["kpis"]["attributed_leads"], 2)
        self.assertEqual(panel["kpis"]["won_leads"], 1)
        self.assertEqual(panel["campaigns"][0]["metrics"]["lead_count"], 2)
        self.assertEqual(panel["campaigns"][0]["metrics"]["conversion_rate"], 50.0)

        task_response = self.post_json(
            f"/api/v1/marketing-campaigns/{campaign_id}/tasks",
            {
                "title": "Complete creative assets",
                "owner_id": self.employee.id,
                "due_date": timezone.localdate().isoformat(),
                "priority": "high",
            },
        )
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.json()["id"]
        complete_response = self.patch_json(
            f"/api/v1/marketing-campaigns/tasks/{task_id}",
            {"status": "done"},
        )
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.json()["status"], "done")
        self.assertIsNotNone(complete_response.json()["completed_at"])

        update_response = self.post_json(
            f"/api/v1/marketing-campaigns/{campaign_id}/updates",
            {
                "update_type": "blocker",
                "text": "Landing page delayed.",
                "blocker": "Landing page copy approval is blocking launch.",
                "next_action": "CEO to approve final copy.",
            },
        )
        self.assertEqual(update_response.status_code, 201)
        self.assertIsNotNone(update_response.json()["created_risk"])
        self.assertEqual(
            CampaignRisk.objects.filter(campaign_id=campaign_id).count(), 1
        )

        expense_response = self.post_json(
            f"/api/v1/marketing-campaigns/{campaign_id}/expenses",
            {
                "vendor": "Meta Ads",
                "amount": "75000.00",
                "category": "paid_media",
                "status": "paid",
            },
        )
        self.assertEqual(expense_response.status_code, 201)
        self.assertEqual(
            CampaignExpense.objects.filter(campaign_id=campaign_id).count(), 1
        )

        asset_response = self.post_json(
            f"/api/v1/marketing-campaigns/{campaign_id}/assets",
            {
                "name": "Estate walkthrough video",
                "asset_type": "video",
                "owner_id": self.employee.id,
                "status": "briefed",
            },
        )
        self.assertEqual(asset_response.status_code, 201)
        asset_id = asset_response.json()["id"]
        asset_update_response = self.patch_json(
            f"/api/v1/marketing-campaigns/assets/{asset_id}",
            {"status": "approved"},
        )
        self.assertEqual(asset_update_response.status_code, 200)
        self.assertEqual(asset_update_response.json()["status"], "approved")

        decision_response = self.post_json(
            f"/api/v1/marketing-campaigns/{campaign_id}/decisions",
            {
                "decision": "Launch once landing page copy is approved.",
                "owner": "Marketing Manager",
                "approver": "CEO",
            },
        )
        self.assertEqual(decision_response.status_code, 201)

        post_response = self.put_json(
            f"/api/v1/marketing-campaigns/{campaign_id}/post-analysis",
            {
                "conclusion": "Campaign generated qualified demand.",
                "worked": "Audience targeting was strong.",
                "failed": "Approval cycle was slow.",
                "lessons": "Approve landing page copy before launch.",
                "mark_campaign_completed": True,
            },
        )
        self.assertEqual(post_response.status_code, 200)
        campaign = MarketingCampaign.objects.get(id=campaign_id)
        self.assertEqual(campaign.status, "completed")

        workspace_response = self.client.get(
            f"/api/v1/marketing-campaigns/{campaign_id}/workspace",
            **self.headers,
        )
        self.assertEqual(workspace_response.status_code, 200)
        workspace = workspace_response.json()
        self.assertEqual(workspace["tasks"]["summary"]["done"], 1)
        self.assertEqual(workspace["assets"]["summary"]["total"], 1)
        self.assertEqual(workspace["risks"]["summary"]["open"], 1)
        self.assertEqual(len(workspace["decisions"]), 1)
        self.assertEqual(
            workspace["post_analysis"]["conclusion"],
            "Campaign generated qualified demand.",
        )

    def test_campaign_request_conversion_and_export(self):
        request_response = self.post_json(
            "/api/v1/marketing-campaigns/requests",
            {
                "title": "ESUT Campus Activation",
                "department": "Marketing",
                "division": "benji",
                "priority": "high",
                "proposed_budget": "350000.00",
                "problem": "Generate campus demand for Benji.",
                "audience": "Students and vendors around ESUT.",
                "expected_outcome": "More qualified Benji leads.",
            },
        )
        self.assertEqual(request_response.status_code, 201)
        request_id = request_response.json()["id"]
        self.assertEqual(CampaignRequest.objects.filter(id=request_id).count(), 1)

        review_response = self.patch_json(
            f"/api/v1/marketing-campaigns/requests/{request_id}",
            {"status": "approved", "review_note": "Approved for launch planning."},
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["status"], "approved")

        convert_response = self.post_json(
            f"/api/v1/marketing-campaigns/requests/{request_id}/convert",
            {"channel": "social_media", "status": "draft"},
        )
        self.assertEqual(convert_response.status_code, 201)
        self.assertEqual(convert_response.json()["request"]["status"], "converted")
        self.assertEqual(
            convert_response.json()["campaign"]["name"], "ESUT Campus Activation"
        )

        export_response = self.client.get(
            "/api/v1/marketing-campaigns/panel/export",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("Campaign,Status,Channel", export_response.content.decode())

    def test_marketing_meetings_integrate_with_base_meetings_and_campaign_workspace(
        self,
    ):
        campaign_response = self.create_campaign(name="Fortress Optimization Campaign")
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]

        meeting_response = self.post_json(
            "/api/v1/marketing/meetings",
            {
                "title": "Fortress weekly optimization review",
                "agenda": "Review lead quality, creative fatigue, budget shifts and blockers.",
                "meeting_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
                "meeting_time": "10:00",
                "duration_minutes": 45,
                "status": "scheduled",
                "location_type": "virtual",
                "location": "Google Meet",
                "attendee_ids": [self.user.id],
                "notes": "Minutes pending.",
                "campaign_id": campaign_id,
                "meeting_type": "live_optimization_review",
                "facilitator": "Marketing Manager",
                "recorder": "Digital Marketer",
                "pre_read": "Latest campaign panel and sales objection report.",
                "expected_outcome": "Approve next creative and budget action.",
            },
        )
        self.assertEqual(meeting_response.status_code, 201)
        meeting = meeting_response.json()
        meeting_id = meeting["id"]
        self.assertEqual(Meeting.objects.count(), 1)
        self.assertEqual(MarketingMeetingContext.objects.count(), 1)
        self.assertEqual(meeting["campaign_id"], campaign_id)
        self.assertEqual(meeting["attendee_count"], 1)

        action_response = self.post_json(
            f"/api/v1/marketing/meetings/{meeting_id}/actions",
            {
                "title": "Send new testimonial creative brief",
                "owner_id": self.employee.id,
                "due_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
                "priority": "high",
            },
        )
        self.assertEqual(action_response.status_code, 201)
        action_id = action_response.json()["id"]
        self.assertEqual(MarketingMeetingAction.objects.count(), 1)

        decision_response = self.post_json(
            f"/api/v1/marketing/meetings/{meeting_id}/decisions",
            {
                "decision": "Shift 20 percent of spend to the testimonial creative.",
                "owner": "Digital Marketer",
                "approver": "Marketing Manager",
                "reason": "Creative has better qualified lead rate.",
            },
        )
        self.assertEqual(decision_response.status_code, 201)
        self.assertEqual(decision_response.json()["source_meeting_id"], meeting_id)

        list_response = self.client.get(
            f"/api/v1/marketing/meetings?status=upcoming&campaign_id={campaign_id}&search=optimization",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        panel = list_response.json()
        self.assertEqual(panel["kpis"]["total_meetings"], 1)
        self.assertEqual(panel["kpis"]["open_action_items"], 1)
        self.assertEqual(panel["kpis"]["decisions_recorded"], 1)
        self.assertEqual(panel["meetings"][0]["id"], meeting_id)

        detail_response = self.client.get(
            f"/api/v1/marketing/meetings/{meeting_id}", **self.headers
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(
            detail["actions"][0]["title"], "Send new testimonial creative brief"
        )
        self.assertEqual(
            detail["decisions"][0]["decision"],
            "Shift 20 percent of spend to the testimonial creative.",
        )

        update_response = self.patch_json(
            f"/api/v1/marketing/meetings/{meeting_id}",
            {
                "status": "completed",
                "notes": "Budget shift approved.",
                "expected_outcome": "Decision recorded.",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["status"], "completed")
        self.assertEqual(update_response.json()["notes"], "Budget shift approved.")

        complete_action_response = self.patch_json(
            f"/api/v1/marketing/meetings/actions/{action_id}",
            {"status": "done"},
        )
        self.assertEqual(complete_action_response.status_code, 200)
        self.assertIsNotNone(complete_action_response.json()["completed_at"])

        workspace_response = self.client.get(
            f"/api/v1/marketing-campaigns/{campaign_id}/workspace",
            **self.headers,
        )
        self.assertEqual(workspace_response.status_code, 200)
        workspace = workspace_response.json()
        self.assertEqual(workspace["meetings"]["summary"]["total"], 1)
        self.assertEqual(workspace["meetings"]["summary"]["completed"], 1)
        self.assertEqual(workspace["meetings"]["items"][0]["decision_count"], 1)

        export_response = self.client.get(
            f"/api/v1/marketing/meetings/export?campaign_id={campaign_id}",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("Meeting,Type,Campaign", export_response.content.decode())

        marketing_only_role = Role.objects.create(
            name="Marketing Meetings Read Only",
            permissions={"marketing_campaigns": ["list", "view"]},
        )
        marketing_only_user = User.objects.create_user(
            email="marketing.meetings.readonly@example.com",
            username="marketingmeetingsreadonly",
            password="password123",
        )
        Employee.objects.create(
            user=marketing_only_user,
            employee_id="EMP-MM-READ",
            role=marketing_only_role,
            is_active=True,
        )
        marketing_only_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(marketing_only_user.id)['access']}"
        }
        denied_create_response = self.client.post(
            "/api/v1/marketing/meetings",
            data=json.dumps(
                {
                    "title": "Denied meeting",
                    "agenda": "Should fail.",
                    "meeting_date": timezone.localdate().isoformat(),
                    "meeting_time": "09:00",
                }
            ),
            content_type="application/json",
            **marketing_only_headers,
        )
        self.assertEqual(denied_create_response.status_code, 403)

        meetings_only_role = Role.objects.create(
            name="Meetings Only",
            permissions={"meetings": ["create", "update", "view", "list"]},
        )
        meetings_only_user = User.objects.create_user(
            email="meetings.only@example.com",
            username="meetingsonly",
            password="password123",
        )
        Employee.objects.create(
            user=meetings_only_user,
            employee_id="EMP-MM-MEET",
            role=meetings_only_role,
            is_active=True,
        )
        meetings_only_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(meetings_only_user.id)['access']}"
        }
        denied_list_response = self.client.get(
            "/api/v1/marketing/meetings", **meetings_only_headers
        )
        self.assertEqual(denied_list_response.status_code, 403)

    def test_traditional_media_register_dashboard_filters_patch_export_and_permissions(
        self,
    ):
        branch = Branch.objects.create(
            branch_name="Traditional Media Branch",
            branch_id="TM-001",
            country="Nigeria",
            state="Enugu",
            office_address="1 Media Road",
            contact_email="traditional.media@example.com",
            contact_phone="08030006666",
        )
        self.employee.branch = branch
        self.employee.save(update_fields=["branch", "updated_at"])
        campaign_response = self.create_campaign(name="Traditional Media Campaign")
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]
        today = timezone.localdate()

        expiring_response = self.post_json(
            "/api/v1/marketing/traditional-media/placements",
            {
                "placement_type": "billboard",
                "name": "New Haven Junction Billboard",
                "vendor": "Prime Outdoor",
                "location": "New Haven Junction",
                "ownership": "rented",
                "amount_paid": "250000.00",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=10)).isoformat(),
                "campaign_id": campaign_id,
                "branch_id": branch.id,
                "division": "real_estate",
                "proof_url": "https://example.com/proof.jpg",
                "notes": "Main estate launch placement.",
            },
        )
        self.assertEqual(expiring_response.status_code, 201)
        expiring = expiring_response.json()
        placement_id = expiring["id"]
        self.assertEqual(expiring["expiry_state"], "expiring_soon")
        self.assertEqual(expiring["days_remaining"], 10)
        self.assertEqual(TraditionalMediaPlacement.objects.count(), 1)

        expired_response = self.post_json(
            "/api/v1/marketing/traditional-media/placements",
            {
                "placement_type": "radio",
                "name": "Coal City Radio Jingle",
                "vendor": "Coal City FM",
                "location": "Morning Drive",
                "ownership": "rented",
                "amount_paid": "100000.00",
                "end_date": (today - timedelta(days=1)).isoformat(),
                "campaign_id": campaign_id,
                "branch_id": branch.id,
                "division": "real_estate",
            },
        )
        self.assertEqual(expired_response.status_code, 201)
        self.assertEqual(expired_response.json()["expiry_state"], "expired")

        cancelled_response = self.post_json(
            "/api/v1/marketing/traditional-media/placements",
            {
                "placement_type": "television",
                "name": "Cancelled TV Spot",
                "vendor": "Local TV",
                "location": "Evening News",
                "ownership": "rented",
                "amount_paid": "999999.00",
                "end_date": (today + timedelta(days=20)).isoformat(),
                "status": "cancelled",
                "campaign_id": campaign_id,
                "branch_id": branch.id,
                "division": "real_estate",
            },
        )
        self.assertEqual(cancelled_response.status_code, 201)

        dashboard_response = self.client.get(
            f"/api/v1/marketing/traditional-media/dashboard?campaign_id={campaign_id}&branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.json()
        self.assertEqual(dashboard["kpis"]["total_placements"], 3)
        self.assertEqual(dashboard["kpis"]["active_placements"], 1)
        self.assertEqual(dashboard["kpis"]["expiring_soon"], 1)
        self.assertEqual(dashboard["kpis"]["expired"], 1)
        self.assertEqual(
            Decimal(str(dashboard["kpis"]["total_spend"])), Decimal("350000.00")
        )
        self.assertFalse(dashboard["metadata"]["renew_action_supported"])

        list_response = self.client.get(
            f"/api/v1/marketing/traditional-media/placements?expiry_filter=expiring_soon&search=Junction&campaign_id={campaign_id}",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        listing = list_response.json()
        self.assertEqual(len(listing["placements"]), 1)
        self.assertEqual(listing["placements"][0]["id"], placement_id)
        self.assertIn(
            "PATCH /marketing/traditional-media/placements/{id}",
            listing["data_notes"][1],
        )

        detail_response = self.client.get(
            f"/api/v1/marketing/traditional-media/placements/{placement_id}",
            **self.headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["name"], "New Haven Junction Billboard")

        patch_response = self.patch_json(
            f"/api/v1/marketing/traditional-media/placements/{placement_id}",
            {
                "end_date": (today + timedelta(days=30)).isoformat(),
                "proof_url": "https://example.com/final-proof.jpg",
            },
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["expiry_state"], "active")
        self.assertEqual(patch_response.json()["days_remaining"], 30)
        self.assertEqual(
            patch_response.json()["proof_url"], "https://example.com/final-proof.jpg"
        )

        renew_response = self.client.post(
            f"/api/v1/marketing/traditional-media/placements/{placement_id}/renew",
            data=json.dumps({}),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(renew_response.status_code, 404)

        export_response = self.client.get(
            f"/api/v1/marketing/traditional-media/placements/export?campaign_id={campaign_id}",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        csv_text = export_response.content.decode()
        self.assertIn("ID,Type,Placement", csv_text)
        self.assertIn("New Haven Junction Billboard", csv_text)

        restricted_role = Role.objects.create(
            name="Traditional Media Restricted",
            permissions={"dashboard": ["view"]},
        )
        restricted_user = User.objects.create_user(
            email="traditional.media.restricted@example.com",
            username="traditionalmediarestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-TM-RESTRICT",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }
        restricted_response = self.client.get(
            "/api/v1/marketing/traditional-media/dashboard",
            **restricted_headers,
        )
        self.assertEqual(restricted_response.status_code, 403)

    def test_marketing_analytics_read_only_panel(self):
        branch = Branch.objects.create(
            branch_name="Analytics Branch",
            branch_id="AN-001",
            country="Nigeria",
            state="Enugu",
            office_address="1 Analytics Road",
            contact_email="analytics.branch@example.com",
            contact_phone="08030006666",
        )
        self.employee.branch = branch
        self.employee.save(update_fields=["branch", "updated_at"])
        target = self.create_revenue_target(
            target_value="10000000.00", progress_value="2500000.00"
        )

        campaign_response = self.create_campaign(
            name="Analytics Launch Campaign",
            budget_allocated="1000000.00",
            budget_spent="200000.00",
            impressions=5000,
            ctr="5.00",
        )
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]

        won_response = self.create_lead(
            full_name="Won Analytics Lead",
            phone="08030003001",
            status="won",
            source="facebook_ad",
            division="real_estate",
            estimated_value="4000000.00",
            campaign_id=campaign_id,
            branch_id=branch.id,
            assigned_to_id=self.employee.id,
        )
        qualified_response = self.create_lead(
            full_name="Qualified Analytics Lead",
            phone="08030003002",
            status="qualified",
            source="instagram",
            division="engineering",
            estimated_value="6000000.00",
            campaign_id=campaign_id,
            branch_id=branch.id,
            assigned_to_id=self.employee.id,
        )
        breached_response = self.create_lead(
            full_name="Breached Analytics Lead",
            phone="08030003003",
            status="new",
            source="referral",
            division="real_estate",
            estimated_value="3000000.00",
            branch_id=branch.id,
        )
        self.assertEqual(won_response.status_code, 201)
        self.assertEqual(qualified_response.status_code, 201)
        self.assertEqual(breached_response.status_code, 201)

        Lead.objects.filter(id=qualified_response.json()["id"]).update(
            first_response_at=timezone.now(),
            first_contact_at=timezone.now(),
        )
        Lead.objects.filter(id=breached_response.json()["id"]).update(
            first_response_due_at=timezone.now() - timedelta(minutes=10),
            sla_status="breached",
        )
        self.create_activity(won_response.json()["id"], to_status="won")

        content = Content.objects.create(
            title="Analytics walkthrough",
            content_type="video",
            status="published",
            platform="instagram",
            views=4200,
            author=self.user,
            published_date=timezone.now(),
        )
        ContentCalendarItem.objects.create(
            title="Published analytics reel",
            format="video",
            platform="instagram",
            division="real_estate",
            branch=branch,
            owner=self.employee,
            status="published",
            due_date=timezone.localdate(),
            published_at=timezone.now(),
            campaign_id=campaign_id,
            content=content,
        )
        ContentCalendarItem.objects.create(
            title="Analytics static design",
            format="graphic",
            platform="facebook",
            division="real_estate",
            branch=branch,
            owner=self.employee,
            status="in_progress",
            due_date=timezone.localdate(),
            campaign_id=campaign_id,
        )

        today = timezone.localdate()
        response = self.client.get(
            f"/api/v1/marketing/analytics?period_start={today.replace(day=1).isoformat()}&period_end={today.isoformat()}&branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        analytics = response.json()

        self.assertEqual(analytics["overview"]["leads_this_period"], 3)
        self.assertEqual(
            Decimal(str(analytics["overview"]["revenue_closed"])), Decimal("4000000.00")
        )
        self.assertEqual(
            Decimal(str(analytics["overview"]["avg_deal_value"])), Decimal("4000000.00")
        )
        self.assertEqual(analytics["overview"]["client_score_status"], "unavailable")
        self.assertTrue(
            any(
                row["source"] == "facebook_ad"
                for row in analytics["lead_analytics"]["source_breakdown"]
            )
        )
        self.assertEqual(analytics["lead_analytics"]["new_leads"], 1)
        self.assertEqual(analytics["lead_analytics"]["sla_overdue"], 1)
        self.assertEqual(analytics["content_analytics"]["planned"], 2)
        self.assertEqual(analytics["content_analytics"]["published"], 1)
        self.assertEqual(analytics["content_analytics"]["compliance_pct"], 50.0)
        self.assertEqual(
            analytics["content_analytics"]["top_platform"]["platform"], "instagram"
        )
        self.assertEqual(analytics["campaign_summary"]["total_campaigns"], 1)
        self.assertEqual(analytics["campaign_summary"]["attributed_leads"], 2)
        self.assertEqual(
            Decimal(str(analytics["campaign_summary"]["won_revenue"])),
            Decimal("4000000.00"),
        )
        self.assertEqual(
            Decimal(str(analytics["revenue"]["target"])),
            Decimal(str(target.target_value)),
        )
        self.assertEqual(
            analytics["team_scorecard"][0]["employee_id"], self.employee.id
        )
        self.assertTrue(analytics["data_notes"])

        campaign_filtered = self.client.get(
            f"/api/v1/marketing/analytics?campaign_id={campaign_id}&branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(campaign_filtered.status_code, 200)
        self.assertEqual(campaign_filtered.json()["overview"]["leads_this_period"], 2)

    def test_email_marketing_preview_send_history_and_permissions(self):
        lead_response = self.create_lead(
            full_name="Email Lead",
            phone="08030005001",
            email="shared@example.com",
            status="qualified",
            division="real_estate",
            source="facebook_ad",
        )
        self.assertEqual(lead_response.status_code, 201)
        client_user = User.objects.create_user(
            email="client.email@example.com",
            username="clientemail",
            password="password123",
            first_name="Client",
            last_name="Recipient",
        )
        CustomerClient.objects.create(user=client_user, is_active=True)
        Partner.objects.create(
            name="External Realtor",
            email="partner.email@example.com",
            status="active",
            category="real_estate",
        )

        preview_response = self.post_json(
            "/api/v1/marketing/email/preview",
            {
                "audience_groups": ["marketing_leads", "clients", "partners", "manual"],
                "filters": {"division": "real_estate", "status": "qualified"},
                "manual_recipients": [
                    {"email": "manual@example.com", "name": "Manual Recipient"},
                    {"email": "shared@example.com", "name": "Duplicate Manual"},
                    {"email": "not-an-email", "name": "Invalid Manual"},
                ],
            },
        )
        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.json()
        self.assertEqual(preview["count"], 4)
        self.assertEqual(preview["skipped_count"], 2)
        self.assertEqual(
            {recipient["email"] for recipient in preview["recipients"]},
            {
                "shared@example.com",
                "client.email@example.com",
                "partner.email@example.com",
                "manual@example.com",
            },
        )

        class FakeEmailResponse:
            ok = True
            status_code = 200
            text = ""

        with patch(
            "domains.marketing_sales.api.v1.routers.marketing.send_marketing_email",
            return_value=FakeEmailResponse(),
        ) as send_mock:
            send_response = self.post_json(
                "/api/v1/marketing/email/send",
                {
                    "subject": "Inspection update",
                    "body": "Hello,\nBook your inspection this week.",
                    "audience_groups": ["marketing_leads", "manual"],
                    "filters": {"division": "real_estate", "status": "qualified"},
                    "manual_recipients": [
                        {"email": "manual@example.com", "name": "Manual Recipient"},
                    ],
                },
            )
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(send_mock.call_count, 2)
        sent = send_response.json()
        campaign = sent["campaign"]
        self.assertEqual(campaign["status"], "sent")
        self.assertEqual(campaign["recipient_count"], 2)
        self.assertEqual(campaign["sent_count"], 2)
        self.assertEqual(campaign["failed_count"], 0)
        self.assertEqual(EmailMarketingCampaign.objects.count(), 1)
        self.assertEqual(
            EmailMarketingRecipient.objects.filter(status="sent").count(), 2
        )

        list_response = self.client.get(
            "/api/v1/marketing/email/campaigns?search=Inspection", **self.headers
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)
        campaign_id = list_response.json()["campaigns"][0]["id"]

        detail_response = self.client.get(
            f"/api/v1/marketing/email/campaigns/{campaign_id}", **self.headers
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(len(detail_response.json()["recipients"]), 2)

        audience_response = self.client.get(
            "/api/v1/marketing/email/audiences", **self.headers
        )
        self.assertEqual(audience_response.status_code, 200)
        self.assertEqual(
            [audience["key"] for audience in audience_response.json()["audiences"]],
            ["marketing_leads", "clients", "partners", "employees", "manual"],
        )

        invalid_response = self.post_json(
            "/api/v1/marketing/email/preview",
            {"audience_groups": ["unknown_group"]},
        )
        self.assertEqual(invalid_response.status_code, 400)

        restricted_role = Role.objects.create(
            name="Email Marketing Restricted User",
            permissions={"leads": ["view", "list"]},
        )
        restricted_user = User.objects.create_user(
            email="email.restricted@example.com",
            username="emailrestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-EMAIL-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }
        restricted_response = self.client.get(
            "/api/v1/marketing/email/campaigns", **restricted_headers
        )
        self.assertEqual(restricted_response.status_code, 403)

    def test_partner_operations_invite_portal_leads_reports_commissions_and_permissions(
        self,
    ):
        class FakeEmailResponse:
            status_code = 200
            text = "ok"
            ok = True

        campaign_response = self.create_campaign(name="Partner Estate Push")
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]

        with patch(
            "domains.marketing_sales.api.v1.routers.marketing.send_marketing_email",
            return_value=FakeEmailResponse(),
        ) as send_mock:
            with self.captureOnCommitCallbacks(execute=True):
                invite_response = self.post_json(
                    "/api/v1/marketing/partners/invitations",
                    {
                        "name": "Adaora External Realty",
                        "email": "adaora.partner@example.com",
                        "phone": "08030007777",
                        "category": "real_estate",
                        "invite_url_base": "https://app.example.com/partner",
                    },
                )
        self.assertEqual(invite_response.status_code, 201)
        invite = invite_response.json()
        partner_id = invite["partner"]["id"]
        token = invite["invitation"]["portal_token"]
        self.assertIn("token=", invite["invitation"]["invite_url"])
        self.assertEqual(PartnerInvitation.objects.count(), 1)
        send_mock.assert_called_once()

        task_response = self.post_json(
            "/api/v1/marketing/partners/tasks",
            {
                "partner_id": partner_id,
                "campaign_id": campaign_id,
                "partner_type": "realtor",
                "title": "Register qualified estate buyers",
                "objective": "Qualified inspections for Fortress City",
                "due_date": timezone.localdate().isoformat(),
                "fee": "50000.00",
                "proof_requirement": "Lead registration and inspection evidence",
            },
        )
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.json()["id"]

        session_response = self.client.get(
            f"/api/v1/marketing/partner-portal/session?token={token}"
        )
        self.assertEqual(session_response.status_code, 200)
        session = session_response.json()
        self.assertEqual(session["partner"]["id"], partner_id)
        self.assertEqual(session["tasks"][0]["id"], task_id)
        self.assertEqual(Partner.objects.get(id=partner_id).status, "active")

        report_response = self.client.post(
            f"/api/v1/marketing/partner-portal/reports?token={token}",
            data=json.dumps(
                {
                    "task_id": task_id,
                    "reach": 12000,
                    "lead_count": 8,
                    "proof_url": "https://example.com/proof",
                    "note": "Realtor campaign posted and prospects registered.",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(report_response.status_code, 201)
        report_id = report_response.json()["id"]
        self.assertEqual(PartnerTask.objects.get(id=task_id).status, "report_submitted")

        review_response = self.patch_json(
            f"/api/v1/marketing/partners/reports/{report_id}/review",
            {"status": "approved", "review_note": "Proof accepted."},
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["status"], "approved")
        self.assertEqual(PartnerTask.objects.get(id=task_id).status, "approved")

        portal_lead_response = self.client.post(
            f"/api/v1/marketing/partner-portal/leads?token={token}",
            data=json.dumps(
                {
                    "full_name": "Partner Sourced Buyer",
                    "phone": "08030008888",
                    "email": "buyer.partner@example.com",
                    "division": "real_estate",
                    "campaign_id": campaign_id,
                    "estimated_value": "4000000.00",
                    "notes": "Registered from external realtor portal.",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(portal_lead_response.status_code, 201)
        lead_id = portal_lead_response.json()["id"]
        Lead.objects.filter(id=lead_id).update(status="won")

        lead_detail_response = self.client.get(
            f"/api/v1/leads/{lead_id}", **self.headers
        )
        self.assertEqual(lead_detail_response.status_code, 200)
        self.assertEqual(lead_detail_response.json()["source"], "referral")
        self.assertEqual(lead_detail_response.json()["referral_partner_id"], partner_id)
        self.assertEqual(
            lead_detail_response.json()["referral_partner_name"],
            "Adaora External Realty",
        )

        commission_response = self.post_json(
            "/api/v1/marketing/partners/commissions",
            {
                "partner_id": partner_id,
                "lead_id": lead_id,
                "amount_basis": "4000000.00",
                "commission_rate": "3.00",
            },
        )
        self.assertEqual(commission_response.status_code, 201)
        commission = commission_response.json()
        commission_id = commission["id"]
        self.assertEqual(
            Decimal(str(commission["commission_due"])), Decimal("120000.00")
        )

        early_payment_response = self.patch_json(
            f"/api/v1/marketing/partners/commissions/{commission_id}/mark-paid",
            {"payment_reference": "PAY-001"},
        )
        self.assertEqual(early_payment_response.status_code, 400)

        approve_response = self.patch_json(
            f"/api/v1/marketing/partners/commissions/{commission_id}/approve",
            {"note": "Receipt verified."},
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["status"], "approved")

        paid_response = self.patch_json(
            f"/api/v1/marketing/partners/commissions/{commission_id}/mark-paid",
            {"payment_reference": "PAY-001"},
        )
        self.assertEqual(paid_response.status_code, 200)
        self.assertEqual(paid_response.json()["status"], "paid")

        dashboard_response = self.client.get(
            f"/api/v1/marketing/partners/dashboard?campaign_id={campaign_id}",
            **self.headers,
        )
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.json()
        self.assertEqual(dashboard["kpis"]["active_partners"], 1)
        self.assertEqual(dashboard["kpis"]["referred_leads"], 1)
        self.assertEqual(dashboard["kpis"]["closed_referred_leads"], 1)
        self.assertEqual(
            Decimal(str(dashboard["kpis"]["closed_referred_revenue"])),
            Decimal("4000000.00"),
        )
        self.assertEqual(
            Decimal(str(dashboard["kpis"]["commission_paid"])), Decimal("120000.00")
        )

        directory_response = self.client.get(
            "/api/v1/marketing/partners/directory?search=Adaora",
            **self.headers,
        )
        self.assertEqual(directory_response.status_code, 200)
        self.assertEqual(directory_response.json()["partners"][0]["referred_leads"], 1)

        reports_response = self.client.get(
            f"/api/v1/marketing/partners/reports?partner_id={partner_id}",
            **self.headers,
        )
        self.assertEqual(reports_response.status_code, 200)
        self.assertEqual(reports_response.json()["reports"][0]["status"], "approved")

        restricted_role = Role.objects.create(
            name="Partner Ops Restricted",
            permissions={"dashboard": ["view"]},
        )
        restricted_user = User.objects.create_user(
            email="partner.ops.restricted@example.com",
            username="partneropsrestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-PARTNER-RESTRICT",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }
        restricted_response = self.client.get(
            "/api/v1/marketing/partners/dashboard",
            **restricted_headers,
        )
        self.assertEqual(restricted_response.status_code, 403)

    def test_campaign_workspace_requires_campaign_permissions(self):
        campaign_response = self.create_campaign()
        self.assertEqual(campaign_response.status_code, 201)
        restricted_role = Role.objects.create(
            name="Campaign Restricted User",
            permissions={"leads": ["view", "list"]},
        )
        restricted_user = User.objects.create_user(
            email="campaign.restricted@example.com",
            username="campaignrestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-CAMP-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }

        panel_response = self.client.get(
            "/api/v1/marketing-campaigns/panel", **restricted_headers
        )
        self.assertEqual(panel_response.status_code, 403)
        analytics_response = self.client.get(
            "/api/v1/marketing/analytics", **restricted_headers
        )
        self.assertEqual(analytics_response.status_code, 403)
        task_response = self.client.post(
            f"/api/v1/marketing-campaigns/{campaign_response.json()['id']}/tasks",
            data=json.dumps({"title": "Blocked task"}),
            content_type="application/json",
            **restricted_headers,
        )
        self.assertEqual(task_response.status_code, 403)

    def test_content_calendar_brief_grid_publish_and_export(self):
        branch = Branch.objects.create(
            branch_name="Content Calendar Branch",
            branch_id="CAL-001",
            country="Nigeria",
            state="Enugu",
            office_address="1 Calendar Road",
            contact_email="calendar.branch@example.com",
            contact_phone="08030007777",
        )
        self.employee.branch = branch
        self.employee.save(update_fields=["branch", "updated_at"])
        campaign_response = self.create_campaign()
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())

        brief_response = self.post_json(
            "/api/v1/content/calendar/briefs",
            {
                "title": "Bethel City estate walkthrough",
                "format": "video",
                "platform": "instagram",
                "division": "real_estate",
                "branch_id": branch.id,
                "owner_id": self.employee.id,
                "due_date": today.isoformat(),
                "scheduled_at": timezone.now().isoformat(),
                "campaign_id": campaign_id,
                "funnel_stage": "evaluation",
                "description": "Estate walkthrough for qualified buyers.",
                "call_to_action": "Book inspection",
                "specifications": "Instagram reel",
                "approval_notes": "Use approved pricing only.",
            },
        )
        self.assertEqual(brief_response.status_code, 201)
        brief = brief_response.json()
        self.assertEqual(brief["title"], "Bethel City estate walkthrough")
        self.assertEqual(brief["campaign_id"], campaign_id)
        self.assertIsNotNone(brief["campaign_asset_id"])
        self.assertEqual(
            CampaignAsset.objects.filter(campaign_id=campaign_id).count(), 1
        )

        calendar_response = self.client.get(
            f"/api/v1/content/calendar?week_start={week_start.isoformat()}&division=real_estate",
            **self.headers,
        )
        self.assertEqual(calendar_response.status_code, 200)
        calendar = calendar_response.json()
        self.assertEqual(calendar["kpis"]["total"], 1)
        self.assertEqual(calendar["rows"][0]["title"], "Bethel City estate walkthrough")
        self.assertTrue(any(day["items"] for day in calendar["days"]))

        update_response = self.patch_json(
            f"/api/v1/content/calendar/briefs/{brief['id']}",
            {"status": "in_review", "approval_notes": "Creative ready for review."},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["status"], "in_review")
        self.assertEqual(
            CampaignAsset.objects.get(id=brief["campaign_asset_id"]).status,
            "review",
        )

        publish_response = self.post_json(
            f"/api/v1/content/calendar/briefs/{brief['id']}/publish",
            {
                "body": "Published estate walkthrough.",
                "excerpt": "Book an inspection today.",
                "tags": "estate,inspection",
            },
        )
        self.assertEqual(publish_response.status_code, 200)
        published = publish_response.json()
        content_id = published["content_id"]
        self.assertEqual(published["calendar_item"]["status"], "published")
        self.assertEqual(Content.objects.get(id=content_id).status, "published")
        self.assertEqual(
            CampaignAsset.objects.get(id=brief["campaign_asset_id"]).content_id,
            content_id,
        )

        overdue_response = self.post_json(
            "/api/v1/content/calendar/briefs",
            {
                "title": "Weekly property WA broadcast",
                "format": "text_image",
                "platform": "whatsapp",
                "division": "real_estate",
                "owner_name": "Sales Rep",
                "due_date": (today - timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(overdue_response.status_code, 201)
        overdue_calendar_response = self.client.get(
            f"/api/v1/content/calendar?date_from={(today - timedelta(days=1)).isoformat()}&date_to={today.isoformat()}&status=overdue",
            **self.headers,
        )
        self.assertEqual(overdue_calendar_response.status_code, 200)
        self.assertEqual(overdue_calendar_response.json()["kpis"]["overdue"], 1)

        export_response = self.client.get(
            f"/api/v1/content/calendar/export?week_start={week_start.isoformat()}",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        csv_text = export_response.content.decode()
        self.assertIn("Title,Format,Platform", csv_text)
        self.assertIn("Bethel City estate walkthrough", csv_text)

    def test_content_calendar_includes_standalone_scheduled_content(self):
        scheduled_at = timezone.now() + timedelta(days=1)
        Content.objects.create(
            title="Standalone scheduled post",
            content_type="social_media",
            status="scheduled",
            platform="facebook",
            scheduled_date=scheduled_at,
            author=self.user,
        )
        week_start = scheduled_at.date() - timedelta(days=scheduled_at.date().weekday())

        response = self.client.get(
            f"/api/v1/content/calendar?week_start={week_start.isoformat()}&platform=facebook",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "content")
        self.assertEqual(
            rows[0]["content_id"],
            Content.objects.get(title="Standalone scheduled post").id,
        )

    def test_content_calendar_requires_content_permissions(self):
        restricted_role = Role.objects.create(
            name="Content Calendar Restricted User",
            permissions={"leads": ["view", "list"]},
        )
        restricted_user = User.objects.create_user(
            email="content.restricted@example.com",
            username="contentrestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-CONTENT-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }

        read_response = self.client.get(
            "/api/v1/content/calendar", **restricted_headers
        )
        self.assertEqual(read_response.status_code, 403)
        write_response = self.client.post(
            "/api/v1/content/calendar/briefs",
            data=json.dumps({"title": "No access"}),
            content_type="application/json",
            **restricted_headers,
        )
        self.assertEqual(write_response.status_code, 403)

    def test_media_library_assets_list_detail_update_export_and_campaign_link(self):
        campaign_response = self.create_campaign()
        self.assertEqual(campaign_response.status_code, 201)
        campaign_id = campaign_response.json()["id"]
        today = timezone.localdate()

        brief_response = self.post_json(
            "/api/v1/content/calendar/briefs",
            {
                "title": "Media linked walkthrough",
                "format": "video",
                "platform": "instagram",
                "division": "real_estate",
                "owner_id": self.employee.id,
                "due_date": today.isoformat(),
                "campaign_id": campaign_id,
                "description": "Video brief linked to media library.",
            },
        )
        self.assertEqual(brief_response.status_code, 201)
        brief = brief_response.json()

        publish_response = self.post_json(
            f"/api/v1/content/calendar/briefs/{brief['id']}/publish",
            {"body": "Published media linked walkthrough."},
        )
        self.assertEqual(publish_response.status_code, 200)
        content_id = publish_response.json()["content_id"]

        create_response = self.post_json(
            "/api/v1/content/media-library/assets",
            {
                "title": "Bethel City Drone Footage",
                "asset_type": "video",
                "file_url": "https://cdn.example.com/bethel-drone.mp4",
                "thumbnail_url": "https://cdn.example.com/bethel-drone.jpg",
                "mime_type": "video/mp4",
                "file_size_bytes": 251658240,
                "division": "real_estate",
                "owner_id": self.employee.id,
                "campaign_asset_id": brief["campaign_asset_id"],
                "calendar_item_id": brief["id"],
                "content_id": content_id,
                "tags": "estate,drone,inspection",
                "description": "Approved drone footage for launch assets.",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        media_asset = create_response.json()
        self.assertEqual(media_asset["campaign_id"], campaign_id)
        self.assertEqual(media_asset["campaign_asset_id"], brief["campaign_asset_id"])
        self.assertEqual(media_asset["content_id"], content_id)
        self.assertEqual(media_asset["display_size"], "240.0 MB")
        asset_id = media_asset["id"]

        list_response = self.client.get(
            "/api/v1/content/media-library?asset_type=video&division=real_estate&search=Drone",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        library = list_response.json()
        self.assertEqual(library["summary"]["total_assets"], 1)
        self.assertEqual(library["summary"]["total_size_display"], "240.0 MB")
        self.assertEqual(library["assets"][0]["id"], asset_id)
        self.assertEqual(library["assets"][0]["icon"], "ti-video")

        detail_response = self.client.get(
            f"/api/v1/content/media-library/assets/{asset_id}",
            **self.headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["links"]["campaign"]["id"], campaign_id)
        self.assertEqual(detail_response.json()["links"]["content"]["id"], content_id)

        patch_response = self.patch_json(
            f"/api/v1/content/media-library/assets/{asset_id}",
            {"status": "archived", "tags": "archived,drone"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["status"], "archived")
        self.assertEqual(
            MediaLibraryAsset.objects.get(id=asset_id).tags, "archived,drone"
        )

        workspace_response = self.client.get(
            f"/api/v1/marketing-campaigns/{campaign_id}/workspace",
            **self.headers,
        )
        self.assertEqual(workspace_response.status_code, 200)
        workspace_assets = workspace_response.json()["assets"]["items"]
        self.assertEqual(workspace_assets[0]["media_assets"][0]["id"], asset_id)

        export_response = self.client.get(
            "/api/v1/content/media-library/export?status=archived",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        csv_text = export_response.content.decode()
        self.assertIn("Title,Asset Type,Division", csv_text)
        self.assertIn("Bethel City Drone Footage", csv_text)

    def test_media_library_requires_content_permissions(self):
        restricted_role = Role.objects.create(
            name="Media Library Restricted User",
            permissions={"leads": ["view", "list"]},
        )
        restricted_user = User.objects.create_user(
            email="media.restricted@example.com",
            username="mediarestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-MEDIA-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }

        read_response = self.client.get(
            "/api/v1/content/media-library", **restricted_headers
        )
        self.assertEqual(read_response.status_code, 403)
        write_response = self.client.post(
            "/api/v1/content/media-library/assets",
            data=json.dumps(
                {
                    "title": "No access",
                    "file_url": "https://cdn.example.com/no-access.jpg",
                }
            ),
            content_type="application/json",
            **restricted_headers,
        )
        self.assertEqual(write_response.status_code, 403)

    def test_lead_funnel_events_are_recorded_for_create_status_and_activity(self):
        lead_response = self.create_lead(score=55)
        self.assertEqual(lead_response.status_code, 201)
        lead_id = lead_response.json()["id"]

        initial_event = LeadFunnelEvent.objects.get(
            lead_id=lead_id, event_type="initial"
        )
        self.assertEqual(initial_event.to_stage, "discovery")
        self.assertFalse(initial_event.metadata["backfilled"])

        status_response = self.patch_json(
            f"/api/v1/leads/{lead_id}/status",
            {"status": "qualified"},
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(
            LeadFunnelEvent.objects.filter(
                lead_id=lead_id,
                from_stage="discovery",
                to_stage="evaluation",
                event_type="transition",
            ).exists()
        )

        activity_response = self.create_activity(
            lead_id,
            to_status="proposal_sent",
            note="Proposal requested after qualification.",
        )
        self.assertEqual(activity_response.status_code, 201)
        self.assertTrue(
            LeadFunnelEvent.objects.filter(
                lead_id=lead_id,
                from_stage="evaluation",
                to_stage="intent",
                metadata__activity_id=activity_response.json()["id"],
            ).exists()
        )

    def test_daily_execution_templates_open_day_completion_and_metrics(self):
        template_response = self.create_daily_template()
        self.assertEqual(template_response.status_code, 201)
        template_id = template_response.json()["id"]

        open_response = self.post_json("/api/v1/revenue-execution/days/open", {})
        self.assertEqual(open_response.status_code, 200)
        day = open_response.json()
        self.assertEqual(len(day["actions"]), 1)
        self.assertEqual(day["actions"][0]["template_id"], template_id)
        action_id = day["actions"][0]["id"]

        complete_response = self.post_json(
            f"/api/v1/revenue-execution/actions/{action_id}/complete",
            {"completion_note": "All new leads contacted."},
        )
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.json()["status"], "completed")

        rebuild_response = self.post_json(
            "/api/v1/revenue-execution/days/open",
            {"force_rebuild": True},
        )
        self.assertEqual(rebuild_response.status_code, 200)
        self.assertEqual(len(rebuild_response.json()["actions"]), 1)
        self.assertEqual(rebuild_response.json()["actions"][0]["status"], "completed")

        summary_response = self.client.get(
            "/api/v1/revenue-execution/summary", **self.headers
        )
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["completion_pct"], 100)
        self.assertEqual(summary_response.json()["completed_actions"], 1)

        month = timezone.localdate().strftime("%Y-%m")
        monthly_response = self.client.get(
            f"/api/v1/revenue-execution/monthly-summary?month={month}",
            **self.headers,
        )
        self.assertEqual(monthly_response.status_code, 200)
        self.assertEqual(monthly_response.json()["fully_completed_days"], 1)

        reopen_response = self.post_json(
            f"/api/v1/revenue-execution/actions/{action_id}/reopen", {}
        )
        self.assertEqual(reopen_response.status_code, 200)
        self.assertEqual(reopen_response.json()["status"], "open")

    def test_speed_to_lead_queue_and_activity_scorecard(self):
        lead_response = self.create_lead(
            status="negotiation",
            source="facebook_ad",
            estimated_value="12000000.00",
        )
        self.assertEqual(lead_response.status_code, 201)
        lead_id = lead_response.json()["id"]
        Lead.objects.filter(id=lead_id).update(
            first_response_due_at=timezone.now() - timedelta(minutes=10),
            first_response_at=None,
            first_contact_at=None,
            sla_status="breached",
        )

        queue_response = self.client.get(
            "/api/v1/revenue-execution/speed-to-lead-queue",
            **self.headers,
        )
        self.assertEqual(queue_response.status_code, 200)
        queue_items = queue_response.json()
        self.assertTrue(any(item["lead_id"] == lead_id for item in queue_items))

        self.assertEqual(self.create_daily_template().status_code, 201)
        day_response = self.post_json("/api/v1/revenue-execution/days/open", {})
        action_id = day_response.json()["actions"][0]["id"]
        DailyActionInstance.objects.filter(id=action_id).update(owner=self.employee)
        self.assertEqual(
            self.post_json(
                f"/api/v1/revenue-execution/actions/{action_id}/complete",
                {"completion_note": "Execution complete."},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.create_activity(
                lead_id,
                activity_type="phone_call",
                outcome="connected",
                note="First response completed.",
                to_status="contacted",
            ).status_code,
            201,
        )

        scorecard_response = self.client.get(
            "/api/v1/revenue-execution/activity-scorecard",
            **self.headers,
        )
        self.assertEqual(scorecard_response.status_code, 200)
        self.assertTrue(scorecard_response.json())

    def test_command_center_returns_revenue_execution_sections(self):
        self.create_revenue_target(
            target_value="10000000.00", progress_value="2500000.00"
        )
        won_response = self.create_lead(
            full_name="Won Customer",
            phone="08030000001",
            status="won",
            score=100,
            estimated_value="4000000.00",
        )
        self.assertEqual(won_response.status_code, 201)
        active_response = self.create_lead(
            full_name="Pipeline Customer",
            phone="08030000002",
            status="negotiation",
            score=88,
            estimated_value="6000000.00",
            next_follow_up_at=timezone.now().isoformat(),
            next_action="Close negotiation",
        )
        self.assertEqual(active_response.status_code, 201)
        self.assertEqual(self.create_daily_template().status_code, 201)
        self.assertEqual(
            self.post_json("/api/v1/revenue-execution/days/open", {}).status_code, 200
        )

        response = self.client.get(
            "/api/v1/revenue-execution/command-center", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("hero", data)
        self.assertIn("kpi_cards", data)
        self.assertIn("priorities", data)
        self.assertIn("management_rhythm", data)
        self.assertIn("executive_risks", data)
        self.assertNotIn("lead_kpis", data)
        self.assertEqual(data["hero"]["ninety_day_target"], "10000000.00")
        self.assertEqual(data["hero"]["executive_review"], "Every Friday · 4 PM")
        self.assertEqual(len(data["kpi_cards"]), 5)
        self.assertEqual(
            [card["label"] for card in data["kpi_cards"]],
            [
                "Revenue closed",
                "Weighted forecast",
                "Qualified pipeline",
                "Follow-up compliance",
                "Daily execution",
            ],
        )
        self.assertEqual(len(data["diagnosis"]), 6)
        self.assertEqual(len(data["funnel"]), 6)
        self.assertEqual(len(data["management_rhythm"]), 4)
        self.assertEqual(len(data["executive_risks"]), 4)

    def test_forecast_returns_lead_derived_coverage_quality_and_export(self):
        self.create_revenue_target(target_value="100000000.00", progress_value="0.00")
        forecast_leads = [
            {
                "full_name": "New Forecast Lead",
                "phone": "08030100001",
                "status": "new",
                "estimated_value": "10000000.00",
                "division": "real_estate",
                "next_follow_up_at": timezone.now().isoformat(),
                "next_action": "Call now",
            },
            {
                "full_name": "Qualified Forecast Lead",
                "phone": "08030100002",
                "status": "qualified",
                "estimated_value": "20000000.00",
                "division": "engineering",
                "next_follow_up_at": timezone.now().isoformat(),
                "next_action": "Book inspection",
            },
            {
                "full_name": "Proposal Forecast Lead",
                "phone": "08030100003",
                "status": "proposal_sent",
                "estimated_value": "30000000.00",
                "division": "real_estate",
                "next_action": "Follow proposal",
            },
            {
                "full_name": "Negotiation Forecast Lead",
                "phone": "08030100004",
                "status": "negotiation",
                "estimated_value": "40000000.00",
                "division": "engineering",
                "next_action": "Close negotiation",
            },
        ]
        for lead_payload in forecast_leads:
            response = self.create_lead(**lead_payload)
            self.assertEqual(response.status_code, 201)

        response = self.client.get(
            "/api/v1/revenue-execution/forecast",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hero"]["weighted_forecast"], "49500000.00")
        self.assertEqual(data["hero"]["target"], "100000000.00")
        self.assertEqual(data["hero"]["progress_percentage"], "49.50")
        self.assertEqual(data["hero"]["target_gap"], "50500000.00")
        self.assertEqual(data["hero"]["scenario"], "base")
        self.assertEqual(data["kpi_cards"][0]["value"], "100000000.00")
        self.assertEqual(data["kpi_cards"][1]["display_value"], "1.00×")
        self.assertEqual(data["kpi_cards"][2]["value"], "83.33")
        self.assertEqual(len(data["division_rows"]), 2)
        self.assertEqual(
            {row["division"]: row["target_gap"] for row in data["division_rows"]},
            {"real_estate": None, "engineering": None},
        )
        self.assertEqual(
            {
                control["key"]: control["supported"]
                for control in data["quality_controls"]
            },
            {
                "value_present": True,
                "next_action_scheduled": True,
                "stage_age_within_limit": True,
                "close_date_verified": False,
                "decision_maker_recorded": False,
            },
        )
        self.assertEqual(data["methodology"]["source"], "lead")
        self.assertEqual(
            [option["key"] for option in data["scenario_options"]],
            ["conservative", "base", "stretch"],
        )

        stretch_response = self.client.get(
            "/api/v1/revenue-execution/forecast?scenario=stretch&division=real_estate",
            **self.headers,
        )
        self.assertEqual(stretch_response.status_code, 200)
        stretch = stretch_response.json()
        self.assertEqual(stretch["hero"]["scenario"], "stretch")
        self.assertEqual(stretch["hero"]["weighted_forecast"], "19840000.00")
        self.assertEqual(len(stretch["division_rows"]), 1)
        self.assertEqual(stretch["division_rows"][0]["division"], "real_estate")

        export_response = self.client.get(
            "/api/v1/revenue-execution/forecast/export?scenario=base",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response["Content-Type"], "text/csv")
        csv_text = export_response.content.decode()
        self.assertIn(
            '"Division","Opportunities","Pipeline","Weighted forecast","Target gap"',
            csv_text,
        )
        self.assertIn('"Real Estate"', csv_text)

    def test_lead_control_filters_auto_assign_and_repair_next_actions(self):
        lead_response = self.create_lead(
            full_name="Unassigned Hot Lead",
            phone="08030000003",
            assigned_to_id=None,
            status="new",
            score=92,
            next_action="",
            next_follow_up_at=None,
        )
        self.assertEqual(lead_response.status_code, 201)
        lead_id = lead_response.json()["id"]
        Lead.objects.filter(id=lead_id).update(
            assigned_to=None,
            first_response_due_at=timezone.now() - timedelta(minutes=5),
            first_response_at=None,
            first_contact_at=None,
            sla_status="breached",
        )

        breach_response = self.client.get(
            "/api/v1/revenue-execution/lead-control?filter=breach",
            **self.headers,
        )
        self.assertEqual(breach_response.status_code, 200)
        self.assertEqual(breach_response.json()["count"], 1)
        self.assertEqual(breach_response.json()["rows"][0]["id"], lead_id)
        self.assertEqual(breach_response.json()["filter"], "breach")
        self.assertEqual(
            [card["label"] for card in breach_response.json()["kpi_cards"]],
            [
                "New & uncontacted",
                "SLA breaches",
                "Hot leads",
                "Stale opportunities",
            ],
        )
        self.assertEqual(
            [rule["points"] for rule in breach_response.json()["scoring_model"]],
            [40, 30, 20, 10],
        )
        self.assertEqual(len(breach_response.json()["qualification_checklist"]), 6)
        row = breach_response.json()["rows"][0]
        self.assertIn("lead", row)
        self.assertIn("lead_meta", row)
        self.assertIn("age_days", row)
        self.assertIn("owner", row)
        self.assertNotIn("phone", row)
        self.assertNotIn("email", row)

        alias_response = self.client.get(
            "/api/v1/revenue-execution/lead-control?filter=sla_breaches",
            **self.headers,
        )
        self.assertEqual(alias_response.status_code, 200)
        self.assertEqual(alias_response.json()["filter"], "breach")

        assign_response = self.post_json(
            "/api/v1/revenue-execution/lead-control/auto-assign", {}
        )
        self.assertEqual(assign_response.status_code, 200)
        self.assertEqual(assign_response.json()["assigned_count"], 1)
        lead = Lead.objects.get(id=lead_id)
        self.assertEqual(lead.assigned_to_id, self.employee.id)

        repair_response = self.post_json(
            "/api/v1/revenue-execution/lead-control/repair-next-actions", {}
        )
        self.assertEqual(repair_response.status_code, 200)
        self.assertEqual(repair_response.json()["repaired_count"], 1)
        lead.refresh_from_db()
        self.assertTrue(lead.next_action)
        self.assertIsNotNone(lead.next_follow_up_at)

    def test_sales_playbook_crud_current_lookup_objections_and_permissions(self):
        branch = Branch.objects.create(
            branch_name="Sales Playbook Branch",
            branch_id="PB-001",
            country="Nigeria",
            state="Enugu",
            office_address="1 Playbook Road",
            contact_email="playbook.branch@example.com",
            contact_phone="08030005555",
        )
        company_payload = {
            "title": "Real Estate Discovery - Individual Buyer",
            "division": "real_estate",
            "stage": "discovery",
            "persona": "individual_buyer",
            "objective": "Understand the buyer outcome before recommending land.",
            "opening_script": "Hello [Name], thank you for your interest.",
            "questions": [
                "What are you buying for?",
                "Which location and budget range are realistic?",
            ],
            "proof_to_use": "Survey, allocation evidence and inspection schedule.",
            "primary_cta": "Book an inspection.",
            "exit_criteria": "Need, budget and next appointment are recorded.",
            "status": "active",
        }
        company_response = self.post_json(
            "/api/v1/revenue-execution/playbooks", company_payload
        )
        self.assertEqual(company_response.status_code, 201)
        company_playbook = company_response.json()
        self.assertEqual(company_playbook["questions"], company_payload["questions"])
        self.assertEqual(SalesPlaybook.objects.count(), 1)

        duplicate_response = self.post_json(
            "/api/v1/revenue-execution/playbooks", company_payload
        )
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertIn("active playbook", duplicate_response.json()["detail"])

        branch_payload = {
            **company_payload,
            "title": "Branch Real Estate Discovery",
            "branch_id": branch.id,
            "opening_script": "Branch-specific opening script.",
        }
        branch_response = self.post_json(
            "/api/v1/revenue-execution/playbooks", branch_payload
        )
        self.assertEqual(branch_response.status_code, 201)
        branch_playbook = branch_response.json()

        objection_response = self.post_json(
            f"/api/v1/revenue-execution/playbooks/{branch_playbook['id']}/objections",
            {
                "objection": "It is too expensive.",
                "response": "Clarify whether the issue is value, cash flow, trust or timing.",
                "sort_order": 1,
            },
        )
        self.assertEqual(objection_response.status_code, 201)
        objection_id = objection_response.json()["id"]
        self.assertEqual(SalesPlaybookObjection.objects.count(), 1)

        list_response = self.client.get(
            "/api/v1/revenue-execution/playbooks?division=real_estate&stage=discovery&persona=individual_buyer&status=active&search=Branch",
            **self.headers,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["count"], 1)
        self.assertEqual(
            list_response.json()["playbooks"][0]["id"], branch_playbook["id"]
        )

        current_response = self.client.get(
            f"/api/v1/revenue-execution/playbooks/current?division=real_estate&stage=discovery&persona=individual_buyer&branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(current_response.status_code, 200)
        self.assertEqual(current_response.json()["id"], branch_playbook["id"])
        self.assertEqual(current_response.json()["objections"][0]["id"], objection_id)

        fallback_archive_response = self.client.delete(
            f"/api/v1/revenue-execution/playbooks/{branch_playbook['id']}",
            **self.headers,
        )
        self.assertEqual(fallback_archive_response.status_code, 200)
        branch_record = SalesPlaybook.objects.get(id=branch_playbook["id"])
        self.assertEqual(branch_record.status, "archived")

        fallback_response = self.client.get(
            f"/api/v1/revenue-execution/playbooks/current?division=real_estate&stage=discovery&persona=individual_buyer&branch_id={branch.id}",
            **self.headers,
        )
        self.assertEqual(fallback_response.status_code, 200)
        self.assertEqual(fallback_response.json()["id"], company_playbook["id"])

        patch_response = self.patch_json(
            f"/api/v1/revenue-execution/playbooks/{company_playbook['id']}",
            {"primary_cta": "Book a live-video inspection.", "sort_order": 3},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(
            patch_response.json()["primary_cta"], "Book a live-video inspection."
        )
        self.assertEqual(patch_response.json()["sort_order"], 3)

        missing_response = self.client.get(
            "/api/v1/revenue-execution/playbooks/current?division=ict&stage=closing&persona=corporate_client",
            **self.headers,
        )
        self.assertEqual(missing_response.status_code, 404)

        objection_update_response = self.patch_json(
            f"/api/v1/revenue-execution/playbooks/objections/{objection_id}",
            {"response": "Updated objection response."},
        )
        self.assertEqual(objection_update_response.status_code, 200)
        self.assertEqual(
            objection_update_response.json()["response"], "Updated objection response."
        )

        objection_delete_response = self.client.delete(
            f"/api/v1/revenue-execution/playbooks/objections/{objection_id}",
            **self.headers,
        )
        self.assertEqual(objection_delete_response.status_code, 200)
        self.assertFalse(SalesPlaybookObjection.objects.get(id=objection_id).is_active)

        restricted_role = Role.objects.create(
            name="Playbook Restricted User",
            permissions={"leads": ["view", "list"]},
        )
        restricted_user = User.objects.create_user(
            email="playbook.restricted@example.com",
            username="playbookrestricted",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-PLAYBOOK-RESTRICTED",
            role=restricted_role,
            is_active=True,
        )
        restricted_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {JWTService.create_tokens(restricted_user.id)['access']}"
        }
        restricted_response = self.client.get(
            "/api/v1/revenue-execution/playbooks", **restricted_headers
        )
        self.assertEqual(restricted_response.status_code, 403)

    def test_funnel_audit_uses_event_cohorts_for_conversion_and_leaks(self):
        discovery_only = self.create_lead(
            full_name="Discovery Only", phone="08030000004"
        )
        evaluation = self.create_lead(full_name="Evaluation Lead", phone="08030000005")
        intent = self.create_lead(full_name="Intent Lead", phone="08030000006")
        purchase = self.create_lead(
            full_name="Purchase Lead", phone="08030000007", estimated_value="5000000.00"
        )
        self.assertEqual(discovery_only.status_code, 201)
        self.assertEqual(evaluation.status_code, 201)
        self.assertEqual(intent.status_code, 201)
        self.assertEqual(purchase.status_code, 201)

        evaluation_id = evaluation.json()["id"]
        intent_id = intent.json()["id"]
        purchase_id = purchase.json()["id"]
        self.assertEqual(
            self.patch_json(
                f"/api/v1/leads/{evaluation_id}/status", {"status": "qualified"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.patch_json(
                f"/api/v1/leads/{intent_id}/status", {"status": "qualified"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.patch_json(
                f"/api/v1/leads/{intent_id}/status", {"status": "proposal_sent"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.patch_json(
                f"/api/v1/leads/{purchase_id}/status", {"status": "qualified"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.patch_json(
                f"/api/v1/leads/{purchase_id}/status", {"status": "proposal_sent"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.patch_json(
                f"/api/v1/leads/{purchase_id}/status", {"status": "won"}
            ).status_code,
            200,
        )

        response = self.client.get(
            "/api/v1/revenue-execution/funnel-audit", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            [stage["stage"] for stage in data["funnel"]],
            ["discovery", "evaluation", "intent", "purchase", "loyalty"],
        )
        self.assertEqual(data["funnel"][0]["entered"], 4)
        self.assertEqual(data["funnel"][1]["entered"], 3)
        self.assertEqual(data["funnel"][2]["entered"], 2)
        self.assertEqual(data["funnel"][3]["entered"], 1)
        self.assertEqual(data["funnel"][1]["conversion_pct"], 75.0)
        self.assertEqual(data["funnel"][2]["conversion_pct"], 66.67)
        self.assertEqual(data["funnel"][3]["conversion_pct"], 50.0)
        self.assertEqual(data["leaks"][0]["transition"], "Purchase → Loyalty")
        self.assertEqual(data["leaks"][0]["loss_pct"], 100.0)
        self.assertEqual(data["data_quality"]["confidence"], "high")
        self.assertTrue(data["division_conversion"])
        self.assertEqual(len(data["corrective_actions"]), 4)

    def test_funnel_event_backfill_marks_partial_history(self):
        lead = Lead.objects.create(
            full_name="Backfilled Lead",
            phone="08030000008",
            division="real_estate",
            source="referral",
            status="won",
            estimated_value="3000000.00",
        )

        result = backfill_lead_funnel_events(Lead.objects.filter(id=lead.id))
        self.assertGreaterEqual(result["created"], 2)
        self.assertTrue(
            LeadFunnelEvent.objects.filter(
                lead=lead,
                event_type="initial",
                to_stage="discovery",
                metadata__backfilled=True,
            ).exists()
        )
        self.assertTrue(
            LeadFunnelEvent.objects.filter(
                lead=lead,
                to_stage="purchase",
                metadata__inferred_current=True,
                metadata__backfilled=True,
            ).exists()
        )

        response = self.client.get(
            "/api/v1/revenue-execution/funnel-audit", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data_quality"]["confidence"], "partial")

    def test_okrs_manual_and_linked_target_progress(self):
        today = timezone.localdate()
        objective_payload = {
            "title": "Recover Q3 revenue engine",
            "description": "Restore predictable revenue execution.",
            "period_start": today.replace(day=1).isoformat(),
            "period_end": today.isoformat(),
            "owner_id": self.employee.id,
        }
        objective_response = self.post_json(
            "/api/v1/revenue-execution/okrs", objective_payload
        )
        self.assertEqual(objective_response.status_code, 201)
        objective_id = objective_response.json()["id"]

        manual_response = self.post_json(
            f"/api/v1/revenue-execution/okrs/{objective_id}/key-results",
            {
                "title": "Close verified revenue",
                "target_value": "100.00",
                "actual_value": "55.00",
                "unit": "%",
                "progress_mode": "manual",
                "weight": "2.00",
            },
        )
        self.assertEqual(manual_response.status_code, 201)
        self.assertEqual(manual_response.json()["progress_percentage"], "55.00")

        target = self.create_revenue_target(
            target_value="100.00", progress_value="50.00"
        )
        linked_response = self.post_json(
            f"/api/v1/revenue-execution/okrs/{objective_id}/key-results",
            {
                "title": "Team revenue target progress",
                "progress_mode": "employee_target",
                "linked_employee_target_id": target.id,
                "weight": "1.00",
            },
        )
        self.assertEqual(linked_response.status_code, 201)
        self.assertEqual(linked_response.json()["effective_actual_value"], "50.00")
        self.assertEqual(linked_response.json()["progress_percentage"], "50.00")

        list_response = self.client.get(
            "/api/v1/revenue-execution/okrs", **self.headers
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["objectives"][0]["id"], objective_id)
        self.assertIn("label", list_response.json()["objectives"][0])
        self.assertIn("key_results", list_response.json()["objectives"][0])
        self.assertIn(
            "percent", list_response.json()["objectives"][0]["key_results"][0]
        )
        self.assertIn("color", list_response.json()["objectives"][0]["key_results"][0])
        self.assertEqual(RevenueObjective.objects.count(), 1)
        self.assertEqual(RevenueKeyResult.objects.count(), 2)

    def test_targets_summary_uses_existing_role_targets_and_reports(self):
        target = self.create_revenue_target(
            target_value="100.00", progress_value="40.00"
        )
        response = self.client.get(
            "/api/v1/revenue-execution/targets/summary?period=monthly",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"]["target_count"], 1)
        self.assertEqual(data["target_rows"][0]["id"], target.id)
        self.assertEqual(data["target_rows"][0]["actual"], "40.00")
        self.assertEqual(data["target_rows"][0]["label"], "Revenue closed")
        self.assertNotIn("employee_targets", data)
        self.assertNotIn("employee_kpis", data)
        self.assertNotIn("role_kpi_metrics", data)

    def test_turnaround_plan_creation_detail_completion_reopen_and_export(self):
        create_response = self.create_turnaround_plan()
        self.assertEqual(create_response.status_code, 201)
        plan = create_response.json()
        self.assertEqual(plan["total_actions"], 13)
        self.assertEqual(plan["completed_actions"], 0)
        self.assertEqual(plan["completion_pct"], 0)

        detail_response = self.client.get(
            f"/api/v1/revenue-execution/turnaround/plans/{plan['id']}",
            **self.headers,
        )
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()
        self.assertEqual(
            [phase["phase"] for phase in detail["roadmap"]],
            ["stabilise", "standardise", "scale"],
        )
        self.assertEqual(sum(len(phase["actions"]) for phase in detail["roadmap"]), 13)
        self.assertEqual(len(detail["performance_contracts"]), 6)
        self.assertEqual(len(detail["governance_rules"]), 6)
        self.assertEqual(len(detail["evidence"]), 8)

        first_action_id = detail["roadmap"][0]["actions"][0]["id"]
        complete_response = self.post_json(
            f"/api/v1/revenue-execution/turnaround/actions/{first_action_id}/complete",
            {"completion_note": "CRM cleanup started."},
        )
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.json()["status"], "completed")

        updated_detail_response = self.client.get(
            f"/api/v1/revenue-execution/turnaround/plans/{plan['id']}",
            **self.headers,
        )
        self.assertEqual(updated_detail_response.status_code, 200)
        self.assertEqual(updated_detail_response.json()["plan"]["completed_actions"], 1)

        reopen_response = self.post_json(
            f"/api/v1/revenue-execution/turnaround/actions/{first_action_id}/reopen",
            {},
        )
        self.assertEqual(reopen_response.status_code, 200)
        self.assertEqual(reopen_response.json()["status"], "open")

        export_response = self.client.get(
            f"/api/v1/revenue-execution/turnaround/plans/{plan['id']}/export",
            **self.headers,
        )
        self.assertEqual(export_response.status_code, 200)
        csv_text = export_response.content.decode()
        self.assertIn('"Phase","Action","Owner","Week","Status"', csv_text)
        self.assertIn("Clean CRM", csv_text)

    def test_turnaround_activation_archives_prior_active_plan(self):
        first_response = self.create_turnaround_plan(name="First Recovery Plan")
        second_response = self.create_turnaround_plan(name="Second Recovery Plan")
        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        first_id = first_response.json()["id"]
        second_id = second_response.json()["id"]

        first_activate = self.post_json(
            f"/api/v1/revenue-execution/turnaround/plans/{first_id}/activate",
            {},
        )
        self.assertEqual(first_activate.status_code, 200)
        self.assertEqual(first_activate.json()["status"], "active")

        second_activate = self.post_json(
            f"/api/v1/revenue-execution/turnaround/plans/{second_id}/activate",
            {},
        )
        self.assertEqual(second_activate.status_code, 200)
        self.assertEqual(second_activate.json()["status"], "active")

        first_plan = TurnaroundPlan.objects.get(id=first_id)
        self.assertEqual(first_plan.status, "archived")

        active_response = self.client.get(
            "/api/v1/revenue-execution/turnaround/plans/active",
            **self.headers,
        )
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.json()["plan"]["id"], second_id)

    def test_turnaround_requires_revenue_execution_permission(self):
        restricted_role = Role.objects.create(
            name="Restricted Marketing User",
            permissions={"leads": ["list"]},
        )
        restricted_user = User.objects.create_user(
            email="restricted.marketing@example.com",
            username="restrictedmarketing",
            password="password123",
        )
        Employee.objects.create(
            user=restricted_user,
            employee_id="EMP-RESTRICTED-001",
            role=restricted_role,
            is_active=True,
        )
        restricted_token = JWTService.create_tokens(restricted_user.id)["access"]
        restricted_headers = {"HTTP_AUTHORIZATION": f"Bearer {restricted_token}"}

        response = self.client.get(
            "/api/v1/revenue-execution/turnaround/plans",
            **restricted_headers,
        )
        self.assertEqual(response.status_code, 403)

        forecast_response = self.client.get(
            "/api/v1/revenue-execution/forecast",
            **restricted_headers,
        )
        self.assertEqual(forecast_response.status_code, 403)
