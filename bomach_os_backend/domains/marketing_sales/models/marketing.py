from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class MarketingCampaign(models.Model):
    """
    Model to track marketing campaign performance
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("draft", "Draft"),
    ]

    CHANNEL_CHOICES = [
        ("social_media", "Social Media"),
        ("email", "Email"),
        ("search", "Search"),
        ("display", "Display"),
        ("video", "Video"),
        ("other", "Other"),
    ]

    # Campaign Basic Information
    name = models.CharField(
        max_length=255,
        verbose_name=_("Campaign Name"),
        help_text=_("Name of the marketing campaign"),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Brief description of the campaign target audience or purpose"),
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name=_("Status")
    )

    channel = models.CharField(
        max_length=50, choices=CHANNEL_CHOICES, verbose_name=_("Marketing Channel")
    )

    # Performance Metrics
    impressions = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Impressions"),
        help_text=_("Total number of times the campaign was displayed"),
    )

    ctr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("CTR (%)"),
        help_text=_("Click-through rate as a percentage"),
    )

    roi = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("ROI (%)"),
        help_text=_("Return on Investment as a percentage"),
    )

    # Progress/Completion
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Progress (%)"),
        help_text=_("Campaign completion percentage"),
    )

    # Budget Information
    budget_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Budget Allocated"),
        help_text=_("Total budget allocated for the campaign"),
    )

    budget_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Budget Spent"),
        help_text=_("Amount spent so far"),
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    start_date = models.DateField(blank=True, null=True, verbose_name=_("Start Date"))

    end_date = models.DateField(blank=True, null=True, verbose_name=_("End Date"))

    class Meta:
        app_label = "services"
        verbose_name = _("Marketing Campaign")
        verbose_name_plural = _("Marketing Campaigns")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["channel"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    @property
    def budget_remaining(self):
        """Calculate remaining budget"""
        return self.budget_allocated - self.budget_spent

    @property
    def budget_utilization_percentage(self):
        """Calculate budget utilization percentage"""
        if self.budget_allocated > 0:
            return (self.budget_spent / self.budget_allocated) * 100
        return 0

    @property
    def is_over_budget(self):
        """Check if campaign is over budget"""
        return self.budget_spent > self.budget_allocated

    @property
    def clicks(self):
        """Calculate total clicks based on impressions and CTR"""
        if self.impressions > 0 and self.ctr > 0:
            return int((self.ctr / 100) * self.impressions)
        return 0

    def save(self, *args, **kwargs):
        """Override save to calculate progress based on budget spent"""
        if self.budget_allocated > 0:
            self.progress_percentage = (self.budget_spent / self.budget_allocated) * 100
            # Cap at 100%
            if self.progress_percentage > 100:
                self.progress_percentage = 100
        super().save(*args, **kwargs)


class CampaignRequest(models.Model):
    STATUS_CHOICES = [
        ("new", "New"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("converted", "Converted"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    title = models.CharField(max_length=255)
    requester = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_requests",
    )
    department = models.CharField(max_length=120, blank=True)
    division = models.CharField(max_length=30, blank=True)
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_requests",
    )
    needed_by = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    proposed_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    problem = models.TextField()
    audience = models.TextField(blank=True)
    product = models.CharField(max_length=255, blank=True)
    expected_outcome = models.CharField(max_length=255, blank=True)
    context = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="new")
    review_note = models.TextField(blank=True)
    converted_campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["branch", "division"]),
        ]

    def __str__(self):
        return self.title


class CampaignTask(models.Model):
    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("done", "Done"),
        ("blocked", "Blocked"),
    ]

    PRIORITY_CHOICES = CampaignRequest.PRIORITY_CHOICES

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="workspace_tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_tasks",
    )
    owner_name = models.CharField(max_length=120, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_campaign_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["due_date", "-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["owner", "due_date"]),
        ]

    def __str__(self):
        return self.title


class CampaignUpdate(models.Model):
    UPDATE_TYPE_CHOICES = [
        ("progress", "Progress"),
        ("result", "Result"),
        ("blocker", "Blocker"),
        ("decision_request", "Decision Request"),
        ("insight", "Insight"),
        ("handover", "Handover"),
    ]

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="workspace_updates",
    )
    update_type = models.CharField(
        max_length=30, choices=UPDATE_TYPE_CHOICES, default="progress"
    )
    update_date = models.DateField()
    text = models.TextField()
    blocker = models.TextField(blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    author = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-update_date", "-created_at"]
        indexes = [
            models.Index(fields=["campaign", "-update_date"]),
            models.Index(fields=["update_type"]),
        ]

    def __str__(self):
        return f"{self.campaign.name} - {self.update_type}"


class CampaignExpense(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
    ]

    CATEGORY_CHOICES = [
        ("paid_media", "Paid Media"),
        ("creative_production", "Creative Production"),
        ("partners", "Partners / Influencers / Realtors"),
        ("offline_media", "Offline Media / Activation"),
        ("tools", "Tools / Technology"),
        ("contingency", "Contingency"),
        ("other", "Other"),
    ]

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="workspace_expenses",
    )
    expense_date = models.DateField()
    category = models.CharField(
        max_length=40, choices=CATEGORY_CHOICES, default="other"
    )
    vendor = models.CharField(max_length=160)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="requested"
    )
    reference = models.CharField(max_length=160, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_campaign_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-expense_date", "-created_at"]
        indexes = [
            models.Index(fields=["campaign", "-expense_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.vendor} - {self.amount}"


class CampaignAsset(models.Model):
    STATUS_CHOICES = [
        ("briefed", "Briefed"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("approved", "Approved"),
        ("live", "Live"),
        ("rejected", "Rejected"),
    ]

    ASSET_TYPE_CHOICES = [
        ("video", "Video"),
        ("graphic", "Graphic"),
        ("carousel", "Carousel"),
        ("landing_page", "Landing Page"),
        ("email", "Email"),
        ("whatsapp_template", "WhatsApp Template"),
        ("radio_script", "Radio Script"),
        ("billboard_artwork", "Billboard Artwork"),
        ("brochure", "Brochure / PDF"),
        ("sales_kit", "Sales Kit"),
        ("event_material", "Event Material"),
        ("other", "Other"),
    ]

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="workspace_assets",
    )
    name = models.CharField(max_length=255)
    asset_type = models.CharField(
        max_length=40, choices=ASSET_TYPE_CHOICES, default="other"
    )
    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_assets",
    )
    owner_name = models.CharField(max_length=120, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="briefed")
    description = models.TextField(blank=True)
    specifications = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    content = models.ForeignKey(
        "services.Content",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_assets",
    )
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_campaign_assets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["due_date", "-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["asset_type"]),
        ]

    def __str__(self):
        return self.name


class CampaignRisk(models.Model):
    TYPE_CHOICES = [
        ("risk", "Risk"),
        ("blocker", "Blocker"),
        ("issue", "Issue"),
        ("change_request", "Change Request"),
        ("dependency", "Dependency"),
        ("assumption", "Assumption"),
    ]

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("monitoring", "Monitoring"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("closed", "Closed"),
    ]

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="workspace_risks",
    )
    record_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="risk")
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="medium"
    )
    title = models.TextField()
    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_risks",
    )
    owner_name = models.CharField(max_length=120, blank=True)
    due_date = models.DateField(null=True, blank=True)
    mitigation = models.TextField(blank=True)
    impact = models.TextField(blank=True)
    approver = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_campaign_risks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["record_type"]),
            models.Index(fields=["severity"]),
        ]

    def __str__(self):
        return self.title[:120]


class CampaignDecision(models.Model):
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="workspace_decisions",
    )
    decision_date = models.DateField()
    decision = models.TextField()
    owner = models.CharField(max_length=120, blank=True)
    approver = models.CharField(max_length=120, blank=True)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_campaign_decisions",
    )
    source_meeting_context = models.ForeignKey(
        "services.MarketingMeetingContext",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_decisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-decision_date", "-created_at"]
        indexes = [
            models.Index(fields=["campaign", "-decision_date"]),
        ]

    def __str__(self):
        return self.decision[:120]


class MarketingMeetingContext(models.Model):
    MEETING_TYPE_CHOICES = [
        ("general_marketing", "General Marketing"),
        ("pre_campaign_planning", "Pre-Campaign Planning"),
        ("campaign_kickoff", "Campaign Kickoff"),
        ("creative_review", "Creative Review"),
        ("live_optimization_review", "Live Optimization Review"),
        ("sales_alignment", "Sales Alignment"),
        ("budget_review", "Budget Review"),
        ("partner_influencer_briefing", "Partner / Influencer Briefing"),
        ("post_campaign_analysis", "Post-Campaign Analysis"),
        ("crisis_issue", "Crisis / Issue"),
        ("one_on_one_coaching", "One-on-One Coaching"),
    ]

    meeting = models.OneToOneField(
        "user.Meeting",
        on_delete=models.CASCADE,
        related_name="marketing_context",
    )
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_meeting_contexts",
    )
    meeting_type = models.CharField(
        max_length=50,
        choices=MEETING_TYPE_CHOICES,
        default="general_marketing",
    )
    facilitator = models.CharField(max_length=120, blank=True)
    recorder = models.CharField(max_length=120, blank=True)
    pre_read = models.TextField(blank=True)
    expected_outcome = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-meeting__meeting_date", "-meeting__meeting_time"]
        indexes = [
            models.Index(fields=["campaign", "meeting_type"]),
            models.Index(fields=["meeting_type"]),
        ]

    def __str__(self):
        return f"Marketing context: {self.meeting.title}"


class MarketingMeetingAction(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    meeting_context = models.ForeignKey(
        MarketingMeetingContext,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        "user.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_meeting_actions",
    )
    owner_name = models.CharField(max_length=120, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_marketing_meeting_actions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["status", "due_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return self.title


class TraditionalMediaPlacement(models.Model):
    PLACEMENT_TYPE_CHOICES = [
        ("billboard", "Billboard"),
        ("radio", "Radio"),
        ("television", "Television"),
        ("led_screen", "LED Screen"),
        ("print_newspaper", "Print / Newspaper"),
        ("field_activation", "Field Activation"),
        ("branded_vehicle", "Branded Vehicle"),
        ("other", "Other"),
    ]

    OWNERSHIP_CHOICES = [
        ("rented", "Rented"),
        ("company_owned", "Company-owned"),
        ("partnership", "Partnership"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("archived", "Archived"),
        ("cancelled", "Cancelled"),
    ]

    DIVISION_CHOICES = [
        ("real_estate", "Real Estate"),
        ("engineering", "Engineering"),
        ("surveying", "Land Surveying"),
        ("benji", "Benji"),
        ("ict", "ICT / Tech"),
        ("agriculture", "Agriculture"),
    ]

    placement_type = models.CharField(max_length=40, choices=PLACEMENT_TYPE_CHOICES)
    name = models.CharField(max_length=255)
    vendor = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=255, blank=True)
    ownership = models.CharField(
        max_length=30, choices=OWNERSHIP_CHOICES, default="rented"
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    proof_url = models.URLField(max_length=1000, blank=True)
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traditional_media_placements",
    )
    branch = models.ForeignKey(
        "user.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traditional_media_placements",
    )
    division = models.CharField(max_length=30, choices=DIVISION_CHOICES, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_traditional_media_placements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["end_date", "-created_at"]
        indexes = [
            models.Index(fields=["placement_type", "status"]),
            models.Index(fields=["ownership"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["branch", "division"]),
        ]

    def __str__(self):
        return self.name


class PartnerInvitation(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ]

    partner = models.ForeignKey(
        "user.Partner",
        on_delete=models.CASCADE,
        related_name="marketing_invitations",
    )
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    invite_url = models.URLField(max_length=1000, blank=True)
    invited_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_partner_invitations",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["email"]),
            models.Index(fields=["expires_at"]),
        ]

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    def __str__(self):
        return f"{self.partner} - {self.status}"


class PartnerTask(models.Model):
    PARTNER_TYPE_CHOICES = [
        ("realtor", "Realtor"),
        ("influencer", "Influencer"),
        ("institutional_partner", "Institutional Partner"),
        ("external_partner", "External Partner"),
    ]

    STATUS_CHOICES = [
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("report_submitted", "Report Submitted"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
    ]

    partner = models.ForeignKey(
        "user.Partner",
        on_delete=models.CASCADE,
        related_name="marketing_tasks",
    )
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_tasks",
    )
    partner_type = models.CharField(
        max_length=30, choices=PARTNER_TYPE_CHOICES, default="external_partner"
    )
    title = models.CharField(max_length=255)
    objective = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    proof_requirement = models.TextField(blank=True)
    tracking_url = models.URLField(max_length=1000, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="assigned")
    assigned_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_partner_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["status", "due_date", "-created_at"]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["partner_type"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return self.title


class PartnerReport(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    task = models.ForeignKey(
        PartnerTask,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    partner = models.ForeignKey(
        "user.Partner",
        on_delete=models.CASCADE,
        related_name="marketing_reports",
    )
    reach = models.PositiveIntegerField(default=0)
    lead_count = models.PositiveIntegerField(default=0)
    proof_url = models.URLField(max_length=1000, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="submitted"
    )
    reviewed_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_partner_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["task", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.task} - {self.status}"


class PartnerCommission(models.Model):
    STATUS_CHOICES = [
        ("pending_verification", "Pending Verification"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
    ]

    partner = models.ForeignKey(
        "user.Partner",
        on_delete=models.CASCADE,
        related_name="marketing_commissions",
    )
    lead = models.ForeignKey(
        "services.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_commissions",
    )
    amount_basis = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    commission_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="pending_verification"
    )
    approved_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_partner_commissions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["lead"]),
            models.Index(fields=["status"]),
        ]

    def calculate_due(self):
        self.commission_due = (
            self.amount_basis * self.commission_rate / Decimal("100")
        ).quantize(Decimal("0.01"))
        return self.commission_due

    def __str__(self):
        return f"{self.partner} - {self.commission_due} - {self.status}"


class CampaignPostAnalysis(models.Model):
    campaign = models.OneToOneField(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="post_analysis",
    )
    conclusion = models.TextField()
    worked = models.TextField(blank=True)
    failed = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    next_actions = models.TextField(blank=True)
    reusable_assets = models.TextField(blank=True)
    analysis_date = models.DateField()
    approver = models.CharField(max_length=120, blank=True)
    author = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_post_analyses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-analysis_date", "-created_at"]

    def __str__(self):
        return f"Post-analysis: {self.campaign.name}"


class EmailMarketingCampaign(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    subject = models.CharField(max_length=255)
    body = models.TextField()
    audience_groups = models.JSONField(default=list, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    recipient_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_email_marketing_campaigns",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["sent_at"]),
            models.Index(fields=["created_by"]),
        ]

    def __str__(self):
        return self.subject


class EmailMarketingRecipient(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    campaign = models.ForeignKey(
        EmailMarketingCampaign,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    source_group = models.CharField(max_length=50)
    source_object_type = models.CharField(max_length=80, blank=True)
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="skipped")
    provider_status_code = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        ordering = ["email"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["email"]),
            models.Index(fields=["source_group"]),
        ]

    def __str__(self):
        return f"{self.email} - {self.status}"
