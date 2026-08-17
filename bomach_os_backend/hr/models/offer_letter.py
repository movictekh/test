from django.db import models

from .applicant import Applicant
from .base import BaseModel


class OfferLetter(BaseModel):
    class Template(models.TextChoices):
        STANDARD_FULL_TIME = "standard_full_time", "Standard Full-Time"
        STANDARD_PART_TIME = "standard_part_time", "Standard Part-Time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="offer_letters"
    )
    template = models.CharField(
        max_length=50, choices=Template.choices, default=Template.STANDARD_FULL_TIME
    )
    annual_salary = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateTimeField()
    letter_content = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "offer_letters"
        ordering = ["-created_at"]
        verbose_name = "Offer Letter"
        verbose_name_plural = "Offer Letters"
        indexes = [
            models.Index(fields=["applicant"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Offer for {self.applicant.full_name} - {self.get_status_display()}"
