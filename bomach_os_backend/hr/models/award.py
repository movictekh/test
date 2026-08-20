from django.db import models
from .base import BaseModel

class Award(BaseModel):
    AWARD_CATEGORY_CHOICES = [
        ('employee_of_the_month', 'Employee of the month'),
        ('state_excellence_winner', 'State excellence winner'),
        ('best_branch_representative', 'Best branch representative'),
        ('regional_leader', 'Regional leader'),
        ('dependable_team_member', 'Dependable team member'),
        ('other', 'Other'),
    ]

    RANK_LEVEL_CHOICES = [
        ('branch', 'Branch'),
        ('state', 'State'),
        ('inter-state-region', 'Inter state region'),
        ('national', 'National'),
    ]

    title = models.CharField(
        max_length=255,
        help_text="Title of the award (e.g., Employee of the Month)"
    )
    category = models.CharField(
        max_length=100,
        help_text="Category of the award (e.g., Monthly Recognition, Excellence)",
        choices=AWARD_CATEGORY_CHOICES
    )
    date_awarded = models.DateField(
        help_text="Date the award was given"
    )
    rank_level = models.CharField(
        max_length=100,
        help_text="Rank or level of the award (e.g., Enugu State, Headquarters)",
        choices=RANK_LEVEL_CHOICES
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description or reason for the award"
    )

    class Meta:
        db_table = 'awards'
        ordering = ['-date_awarded']
        verbose_name = 'Award'
        verbose_name_plural = 'Awards'
        indexes = [
            models.Index(fields=['date_awarded']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} - ({self.date_awarded})"
