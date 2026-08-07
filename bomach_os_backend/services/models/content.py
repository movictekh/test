from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import uuid


class Content(models.Model):
    """
    Model for managing marketing content (blog posts, social media posts, etc.)
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('blog_post', 'Blog Post'),
        ('social_media', 'Social Media'),
        ('video', 'Video'),
        ('infographic', 'Infographic'),
        ('newsletter', 'Newsletter'),
        ('article', 'Article'),
    ]

    PLATFORM_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('website', 'Website'),
        ('medium', 'Medium'),
        ('youtube', 'YouTube'),
    ]

    # Basic Information
    title = models.CharField(
        max_length=500,
        verbose_name=_("Title"),
        help_text=_("Content title or headline")
    )

    content_type = models.CharField(
        max_length=50,
        choices=CONTENT_TYPE_CHOICES,
        default='blog_post',
        verbose_name=_("Content Type")
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_("Status")
    )

    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        verbose_name=_("Platform"),
        help_text=_("Platform where content is published")
    )

    # Content Details
    body = models.TextField(
        blank=True,
        verbose_name=_("Content Body"),
        help_text=_("Main content/text")
    )

    excerpt = models.TextField(
        blank=True,
        max_length=500,
        verbose_name=_("Excerpt"),
        help_text=_("Short description or summary")
    )

    featured_image = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("Featured Image")
    )

    # Engagement Metrics
    views = models.PositiveIntegerField(default=0, verbose_name=_("Views"))
    likes = models.PositiveIntegerField(default=0, verbose_name=_("Likes"))
    shares = models.PositiveIntegerField(default=0, verbose_name=_("Shares"))
    comments = models.PositiveIntegerField(default=0, verbose_name=_("Comments"))

    # Author
    author = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_content',
        verbose_name=_("Author"),
    )

    # Publishing Information
    published_date = models.DateTimeField(blank=True, null=True, verbose_name=_("Published Date"))
    scheduled_date = models.DateTimeField(blank=True, null=True, verbose_name=_("Scheduled Date"))

    # SEO and URLs
    slug = models.SlugField(max_length=500, unique=True, blank=True, verbose_name=_("URL Slug"))
    external_url = models.URLField(blank=True, verbose_name=_("External URL"))
    meta_description = models.CharField(max_length=160, blank=True, verbose_name=_("Meta Description"))
    keywords = models.CharField(max_length=500, blank=True, verbose_name=_("Keywords"))

    # Tags and Categories
    tags = models.CharField(max_length=500, blank=True, verbose_name=_("Tags"))
    category = models.CharField(max_length=100, blank=True, verbose_name=_("Category"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # Additional Flags
    is_featured = models.BooleanField(default=False, verbose_name=_("Featured"))
    allow_comments = models.BooleanField(default=True, verbose_name=_("Allow Comments"))

    class Meta:
        verbose_name = _("Content")
        verbose_name_plural = _("Content")
        ordering = ['-published_date', '-created_at']
        indexes = [
            models.Index(fields=['status', '-published_date']),
            models.Index(fields=['content_type', 'platform']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    @property
    def engagement_rate(self):
        if self.views > 0:
            total_engagement = self.likes + self.shares + self.comments
            return (total_engagement / self.views) * 100
        return 0

    @property
    def total_engagement(self):
        return self.likes + self.shares + self.comments

    @property
    def is_published(self):
        return self.status == 'published'

    def increment_views(self):
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(views=F('views') + 1)
        self.refresh_from_db(fields=['views'])

    def increment_likes(self):
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(likes=F('likes') + 1)
        self.refresh_from_db(fields=['likes'])

    def increment_shares(self):
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(shares=F('shares') + 1)
        self.refresh_from_db(fields=['shares'])

    def increment_comments(self):
        from django.db.models import F
        self.__class__.objects.filter(pk=self.pk).update(comments=F('comments') + 1)
        self.refresh_from_db(fields=['comments'])


class ContentCalendarItem(models.Model):
    STATUS_CHOICES = [
        ('briefed', 'Briefed'),
        ('in_progress', 'In Progress'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('overdue', 'Overdue'),
        ('archived', 'Archived'),
    ]

    FORMAT_CHOICES = [
        ('video', 'Video'),
        ('graphic', 'Graphic'),
        ('carousel', 'Carousel'),
        ('text_image', 'Text + Image'),
        ('email', 'Email'),
        ('whatsapp_template', 'WhatsApp Template'),
        ('blog_article', 'Blog / Article'),
        ('radio_script', 'Radio Script'),
        ('billboard_artwork', 'Billboard Artwork'),
        ('other', 'Other'),
    ]

    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('tiktok', 'TikTok'),
        ('whatsapp', 'WhatsApp'),
        ('linkedin', 'LinkedIn'),
        ('website', 'Website'),
        ('youtube', 'YouTube'),
        ('email', 'Email'),
        ('multiple', 'Multiple'),
        ('other', 'Other'),
    ]

    FUNNEL_STAGE_CHOICES = [
        ('awareness', 'Awareness'),
        ('discovery', 'Discovery'),
        ('evaluation', 'Evaluation'),
        ('intent', 'Intent'),
        ('purchase', 'Purchase'),
        ('loyalty', 'Loyalty'),
    ]

    DIVISION_CHOICES = [
        ('real_estate', 'Real Estate'),
        ('engineering', 'Engineering'),
        ('surveying', 'Land Surveying'),
        ('benji', 'Benji'),
        ('ict', 'ICT / Tech'),
        ('agriculture', 'Agriculture'),
    ]

    title = models.CharField(max_length=255)
    format = models.CharField(max_length=40, choices=FORMAT_CHOICES, default='other')
    platform = models.CharField(max_length=40, choices=PLATFORM_CHOICES, default='multiple')
    division = models.CharField(max_length=30, choices=DIVISION_CHOICES, blank=True)
    branch = models.ForeignKey(
        'user.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_calendar_items',
    )
    owner = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_calendar_items',
    )
    owner_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='briefed')
    due_date = models.DateField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    campaign = models.ForeignKey(
        'services.MarketingCampaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_calendar_items',
    )
    campaign_asset = models.ForeignKey(
        'services.CampaignAsset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_calendar_items',
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_items',
    )
    funnel_stage = models.CharField(max_length=30, choices=FUNNEL_STAGE_CHOICES, blank=True)
    description = models.TextField(blank=True)
    call_to_action = models.CharField(max_length=255, blank=True)
    specifications = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_content_calendar_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'sort_order', '-created_at']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['platform']),
            models.Index(fields=['division']),
            models.Index(fields=['owner', 'due_date']),
            models.Index(fields=['campaign']),
            models.Index(fields=['branch', 'division']),
        ]

    def __str__(self):
        return self.title


class MediaLibraryAsset(models.Model):
    ASSET_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('design_source', 'Design Source'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    DIVISION_CHOICES = ContentCalendarItem.DIVISION_CHOICES

    title = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPE_CHOICES, default='other')
    file_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    division = models.CharField(max_length=30, choices=DIVISION_CHOICES, blank=True)
    branch = models.ForeignKey(
        'user.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_library_assets',
    )
    owner = models.ForeignKey(
        'user.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_library_assets',
    )
    owner_name = models.CharField(max_length=120, blank=True)
    campaign = models.ForeignKey(
        'services.MarketingCampaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_library_assets',
    )
    campaign_asset = models.ForeignKey(
        'services.CampaignAsset',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_library_assets',
    )
    calendar_item = models.ForeignKey(
        ContentCalendarItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_library_assets',
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='media_library_assets',
    )
    tags = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    uploaded_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_media_library_assets',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['division']),
            models.Index(fields=['branch', 'division']),
            models.Index(fields=['owner']),
            models.Index(fields=['campaign']),
            models.Index(fields=['campaign_asset']),
            models.Index(fields=['content']),
            models.Index(fields=['calendar_item']),
        ]

    def __str__(self):
        return self.title
