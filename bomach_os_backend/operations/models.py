from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    name = models.CharField(max_length=255)
    short_code = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100)
    department = models.ForeignKey(
        'user.Department',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ops_projects',
    )
    client = models.ForeignKey(
        'user.Client',
        on_delete=models.PROTECT,
        related_name='projects',
    )
    employees = models.ManyToManyField(
        'user.Employee',
        blank=True,
        related_name='assigned_projects',
    )
    location = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    summary = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    budget = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    file_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='File URL'
    )
    start_date = models.DateField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['client']),
        ]

    def __str__(self):
        return f"{self.short_code} - {self.name}"


class Milestone(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    budget = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], blank=True, null=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['end_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"{self.name} - {self.project.short_code}"

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='tasks', blank=True, null=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ManyToManyField(
        'user.Employee',
        blank=True,
        related_name='assigned_tasks',
    )
    due_date = models.DateField(blank=True, null=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-priority']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return self.name


class Worksite(models.Model):
    STATUS_CHOICES = [
        ('setup', 'Setup'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='worksites')
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='setup')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"{self.name} - {self.project.short_code}"

class SiteEquipment(models.Model):
    worksite = models.ForeignKey(Worksite, on_delete=models.CASCADE, related_name='equipment')
    name = models.CharField(max_length=255)
    unit_value = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['worksite']),
        ]

    def __str__(self):
        return f"{self.name} - {self.worksite.name}"


class Contract(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    TYPE_CHOICES = [
        ('specialist', 'Specialist'),
        ('project_management', 'Project Management'),
        ('consulting', 'Consulting'),
        ('fixed_price', 'Fixed Price'),
        ('time_materials', 'Time & Materials'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='contracts')
    name = models.CharField(max_length=255)
    contract_number = models.CharField(max_length=50, unique=True)
    contract_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    value = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['contract_number']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.name}"


class Timeline(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='timelines')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"{self.name} - {self.project.short_code}"
