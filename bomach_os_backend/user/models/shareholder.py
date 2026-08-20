from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

from user.models.base import BaseModel
from user.models.user import User
from user.models.employee import Employee


class Shareholder(BaseModel):
    """Model for company shareholders and board members"""

    TITLE_CHOICES = [
        ("founder", "Founder"),
        ("co_founder", "Co Founder"),
        ("chairman", "Chairman"),
        ("vice_chairman", "Vice Chairman"),
        ("executive_director", "Executive Director"),
        ("non_executive_director", "Non-Executive Director"),
        ("board_member", "Board Member"),
    ]

    shareholder_id = models.CharField(
        max_length=50, unique=True, verbose_name="Shareholder ID"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="shareholder_profile",
        verbose_name="User",
    )

    title = models.CharField(
        max_length=50,
        choices=TITLE_CHOICES,
        default="board_member",
        verbose_name="Board Title",
    )
    share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        verbose_name="Share Percentage",
        help_text="Percentage ownership in the company (0.00 - 100.00)",
    )
    share_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Share Count",
        help_text="Number of shares held",
    )
    is_board_member = models.BooleanField(
        default=False,
        verbose_name="Is Board Member",
        help_text="Designates whether this shareholder sits on the board of directors",
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Shareholder"
        verbose_name_plural = "Shareholders"
        ordering = ["-share_percentage", "-created_at"]

    def __str__(self):
        name = (
            f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email
        )
        return f"{name} ({self.share_percentage}%)"

    def clean(self):
        super().clean()
        valid_titles = [c[0] for c in self.TITLE_CHOICES]
        if self.title and self.title not in valid_titles:
            raise ValidationError(
                {"title": f"Invalid title. Must be one of: {', '.join(valid_titles)}"}
            )

    def save(self, *args, **kwargs):
        if not self.shareholder_id:
            self.shareholder_id = f"SH-{uuid.uuid4().hex[:12].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)
