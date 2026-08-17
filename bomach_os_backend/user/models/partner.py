from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from user.models.base import BaseModel


class Partner(BaseModel):
    """Partner record for external partners/companies. Partners cannot login."""

    CATEGORY_CHOICES = [
        ("law_firm", "Law Firm"),
        ("accounting", "Accounting Firm"),
        ("consulting", "Consulting Firm"),
        ("construction", "Construction Company"),
        ("real_estate", "Real Estate Agency"),
        ("financial", "Financial Institution"),
        ("technology", "Technology Company"),
        ("supplier", "Supplier"),
        ("contractor", "Contractor"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("pending", "Pending"),
        ("suspended", "Suspended"),
    ]

    name = models.CharField(max_length=255, verbose_name="Partner Name")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    phone = models.CharField(
        max_length=30, blank=True, default="", verbose_name="Phone"
    )
    address = models.TextField(blank=True, default="", verbose_name="Address")
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="other",
        verbose_name="Category",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="inactive",
        verbose_name="Status",
    )
    notes = models.TextField(blank=True, default="", verbose_name="Notes")

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partners"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class PartnerAgreement(BaseModel):
    """Agreement/document between the company and a partner."""

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name="agreements",
        verbose_name="Partner",
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    document = models.FileField(
        upload_to="partners/agreements/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "png", "jpg", "jpeg"]
            )
        ],
        verbose_name="Document",
    )
    date = models.DateField(verbose_name="Date")

    class Meta:
        verbose_name = "Partner Agreement"
        verbose_name_plural = "Partner Agreements"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.title} - {self.partner.name}"
