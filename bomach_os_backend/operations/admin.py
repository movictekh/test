from django.contrib import admin
from .models import Project, Task, Worksite, Contract, Timeline


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['short_code', 'name', 'status', 'priority', 'budget', 'progress', 'start_date', 'deadline']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['name', 'short_code', 'category', 'client_id']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'milestone', 'status', 'priority', 'due_date', 'estimated_hours']
    list_filter = ['status', 'priority', 'milestone']
    search_fields = ['name', 'description']
    ordering = ['due_date', '-priority']
    date_hierarchy = 'due_date'


@admin.register(Worksite)
class WorksiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'location', 'status']
    list_filter = ['status', 'project']
    search_fields = ['name', 'location']
    ordering = ['-created_at']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'name', 'project', 'contract_type', 'status', 'value', 'start_date', 'end_date']
    list_filter = ['status', 'contract_type', 'project']
    search_fields = ['name', 'contract_number']
    ordering = ['-created_at']
    date_hierarchy = 'start_date'


@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'project']
    search_fields = ['name', 'description']
    ordering = ['start_date']
    date_hierarchy = 'start_date'
