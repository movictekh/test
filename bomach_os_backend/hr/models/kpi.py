from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from .base import BaseModel


class KPIMetric(BaseModel):
    """Reusable KPI metric definition (e.g., 'Attendance', 'Sales Target')."""

    class UnitChoices(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        COUNT = "count", "Count"
        CURRENCY = "currency", "Currency"
        RATING = "rating", "Rating"

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')
    unit = models.CharField(
        max_length=20,
        choices=UnitChoices.choices,
        default=UnitChoices.PERCENTAGE,
    )

    class Meta:
        db_table = 'kpi_metrics'
        ordering = ['name']

    def __str__(self):
        return self.name


class KPITemplate(BaseModel):
    """Groups KPI metrics for a specific department combination."""

    department = models.ForeignKey(
        'user.Department',
        on_delete=models.CASCADE,
        related_name='kpi_templates',
    )
    metrics = models.ManyToManyField(
        KPIMetric,
        through='KPITemplateMetric',
        related_name='templates',
    )

    class Meta:
        db_table = 'kpi_templates'
        ordering = ['department']

    def __str__(self):
        return f"{self.department}"


class KPITemplateMetric(BaseModel):
    """Through table: links a KPI metric to a template with weight and target."""

    template = models.ForeignKey(
        KPITemplate,
        on_delete=models.CASCADE,
        related_name='template_metrics',
    )
    metric = models.ForeignKey(
        KPIMetric,
        on_delete=models.CASCADE,
        related_name='metric_assignments',
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Weight as a percentage (all weights in a template should sum to 100)"
    )
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Target value for this metric"
    )

    class Meta:
        db_table = 'kpi_template_metrics'
        unique_together = ['template', 'metric']
        ordering = ['-weight']

    def __str__(self):
        return f"{self.template} | {self.metric.name} ({self.weight}%)"
