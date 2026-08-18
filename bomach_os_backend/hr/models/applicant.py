from django.db import models, IntegrityError, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import BaseModel
from .job_posting import JobPosting


class Applicant(BaseModel):
    class Education(models.TextChoices):
        HIGH_SCHOOL = 'high_school', 'High School'
        ASSOCIATE = 'associate', 'Associate Degree'
        BACHELOR = 'bachelor', 'Bachelor Degree'
        MASTER = 'master', 'Master Degree'
        DOCTORATE = 'doctorate', 'Doctorate'
        OTHER = 'other', 'Other'

    class Source(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        INDEED = 'indeed', 'Indeed'
        COMPANY_WEBSITE = 'company_website', 'Company Website'
        REFERRAL = 'referral', 'Referral'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        APPLIED = 'applied', 'Applied'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        INTERVIEWED = 'interviewed', 'Interviewed'
        OFFERED = 'offered', 'Offered'
        HIRED = 'hired', 'Hired'
        REJECTED = 'rejected', 'Rejected'

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='applicants'
    )
    
    linkedin_url = models.URLField(blank=True, null=True)
    portolio_url = models.URLField(blank=True, null=True)
    resume = models.URLField(blank=True, null=True)
    cover_letter = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    address = models.CharField(max_length=255, blank=True, null=True)
    current_job_title = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)

    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.APPLIED
    )

    highest_education = models.CharField(
        max_length=100,
        choices=Education.choices,
        blank=True,
        null=True
    )
    institution_name = models.CharField(max_length=255, blank=True, null=True)

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        blank=True,
        null=True
    )

    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'applicants'
        ordering = ['-created_at']
        verbose_name = 'Applicant'
        verbose_name_plural = 'Applicants'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job_posting.job_title}"

    @property
    def full_name(self):
        """Return full name of applicant"""
        return f"{self.first_name} {self.last_name}"
