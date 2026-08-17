from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Event(models.Model):
    """
    Model for managing marketing events and activities
    """

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("postponed", "Postponed"),
    ]

    EVENT_TYPE_CHOICES = [
        ("trade_show", "Trade Show"),
        ("webinar", "Webinar"),
        ("career_fair", "Career Fair"),
        ("conference", "Conference"),
        ("workshop", "Workshop"),
        ("seminar", "Seminar"),
        ("networking", "Networking"),
        ("product_launch", "Product Launch"),
        ("meetup", "Meetup"),
        ("exhibition", "Exhibition"),
    ]

    # Event Basic Information
    name = models.CharField(max_length=500, verbose_name=_("Event Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    event_type = models.CharField(
        max_length=50, choices=EVENT_TYPE_CHOICES, verbose_name=_("Event Type")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="planning",
        verbose_name=_("Status"),
    )

    # Location Information
    venue_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Venue Name")
    )
    venue_address = models.TextField(blank=True, verbose_name=_("Venue Address"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("City"))
    is_online = models.BooleanField(default=False, verbose_name=_("Online Event"))
    online_platform = models.CharField(
        max_length=100, blank=True, verbose_name=_("Online Platform")
    )
    meeting_url = models.URLField(blank=True, verbose_name=_("Meeting URL"))

    # Date and Time
    event_date = models.DateField(verbose_name=_("Event Date"))
    start_time = models.TimeField(blank=True, null=True, verbose_name=_("Start Time"))
    end_time = models.TimeField(blank=True, null=True, verbose_name=_("End Time"))
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_("Duration (Hours)"),
    )

    # Registration Information
    max_registrations = models.PositiveIntegerField(
        default=100, verbose_name=_("Maximum Registrations")
    )
    current_registrations = models.PositiveIntegerField(
        default=0, verbose_name=_("Current Registrations")
    )
    registration_deadline = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Registration Deadline")
    )
    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Registration Fee"),
    )
    currency = models.CharField(max_length=3, default="NGN", verbose_name=_("Currency"))
    allow_registration = models.BooleanField(
        default=True, verbose_name=_("Allow Registration")
    )

    # Event Management
    organizer = models.ForeignKey(
        "user.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organized_events",
        verbose_name=_("Organizer"),
    )

    team_members = models.ManyToManyField(
        "user.User",
        blank=True,
        related_name="event_teams",
        verbose_name=_("Team Members"),
    )

    # Additional Information
    banner_image = models.URLField(
        blank=True, null=True, verbose_name=_("Banner Image")
    )
    thumbnail = models.URLField(blank=True, null=True, verbose_name=_("Thumbnail"))
    tags = models.CharField(max_length=500, blank=True, verbose_name=_("Tags"))
    target_audience = models.CharField(
        max_length=500, blank=True, verbose_name=_("Target Audience")
    )

    # Contact Information
    contact_email = models.EmailField(blank=True, verbose_name=_("Contact Email"))
    contact_phone = models.CharField(
        max_length=20, blank=True, verbose_name=_("Contact Phone")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # Flags
    is_featured = models.BooleanField(default=False, verbose_name=_("Featured Event"))
    is_public = models.BooleanField(default=True, verbose_name=_("Public Event"))
    send_reminders = models.BooleanField(default=True, verbose_name=_("Send Reminders"))

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ["event_date", "start_time"]
        indexes = [
            models.Index(fields=["status", "event_date"]),
            models.Index(fields=["event_type", "-event_date"]),
            models.Index(fields=["organizer", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.event_date}"

    @property
    def registration_percentage(self):
        if self.max_registrations > 0:
            return (self.current_registrations / self.max_registrations) * 100
        return 0

    @property
    def is_full(self):
        return self.current_registrations >= self.max_registrations

    @property
    def available_slots(self):
        return self.max_registrations - self.current_registrations

    @property
    def is_upcoming(self):
        from django.utils import timezone

        return self.event_date >= timezone.now().date()

    @property
    def is_past(self):
        from django.utils import timezone

        return self.event_date < timezone.now().date()

    @property
    def location_display(self):
        if self.is_online:
            return (
                f"Online ({self.online_platform})" if self.online_platform else "Online"
            )
        return (
            f"{self.venue_name}, {self.city}"
            if self.venue_name and self.city
            else self.venue_name or self.city or "TBA"
        )

    def increment_registrations(self):
        if not self.is_full:
            self.current_registrations += 1
            self.save(update_fields=["current_registrations"])
            return True
        return False

    def decrement_registrations(self):
        if self.current_registrations > 0:
            self.current_registrations -= 1
            self.save(update_fields=["current_registrations"])
            return True
        return False


class EventRegistration(models.Model):
    """
    Model to track individual event registrations
    """

    REGISTRATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("attended", "Attended"),
        ("no_show", "No Show"),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name=_("Event"),
    )

    attendee = models.ForeignKey(
        "user.User",
        on_delete=models.CASCADE,
        related_name="event_registrations",
        verbose_name=_("Attendee"),
    )

    status = models.CharField(
        max_length=20,
        choices=REGISTRATION_STATUS_CHOICES,
        default="pending",
        verbose_name=_("Registration Status"),
    )

    registration_date = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Registration Date")
    )

    confirmation_code = models.CharField(
        max_length=50, unique=True, blank=True, verbose_name=_("Confirmation Code")
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("refunded", "Refunded"),
            ("waived", "Waived"),
        ],
        default="pending",
        verbose_name=_("Payment Status"),
    )

    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    class Meta:
        verbose_name = _("Event Registration")
        verbose_name_plural = _("Event Registrations")
        unique_together = ["event", "attendee"]
        ordering = ["-registration_date"]

    def __str__(self):
        return f"{self.attendee} - {self.event.name}"

    def save(self, *args, **kwargs):
        if not self.confirmation_code:
            import uuid

            self.confirmation_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)
