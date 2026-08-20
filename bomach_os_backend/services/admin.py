from django.contrib import admin
from .models import (
    ServiceCategory, Service, ServiceLead, Quote,
    ServiceOrder, Invoice, InvoiceItem, Payment,
    Expense, Property, Document, Lead, LeadActivity,
    LeadFunnelEvent, DailyActionTemplate, DailyExecutionDay, DailyActionInstance,
    RevenueObjective, RevenueKeyResult, TurnaroundPlan, TurnaroundAction
)
from .models.marketing_campaign import MarketingCampaign
from .models.content import Content


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'delivery_time', 'status', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-created_at']


@admin.register(ServiceLead)
class ServiceLeadAdmin(admin.ModelAdmin):
    list_display = ['client_id', 'service', 'estimated_value', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['client_id', 'service__name', 'notes']
    ordering = ['-created_at']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_number', 'client_id', 'service', 'amount', 'valid_until', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['quote_number', 'client_id', 'service__name']
    ordering = ['-created_at']
    readonly_fields = ['quote_number']


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'client_id', 'service', 'amount', 'order_status', 'payment_status', 'created_at']
    list_filter = ['order_status', 'payment_status', 'created_at']
    search_fields = ['order_number', 'client_id', 'service__name']
    ordering = ['-created_at']
    readonly_fields = ['order_number']


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ['total']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client_id', 'service', 'total_amount', 'amount_paid', 'status', 'issue_date', 'due_date']
    list_filter = ['status', 'issue_date', 'created_at']
    search_fields = ['invoice_number', 'client_id', 'service__name']
    ordering = ['-created_at']
    readonly_fields = ['invoice_number', 'tax_amount', 'total_amount', 'balance', 'payment_progress']
    inlines = [InvoiceItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_reference', 'invoice', 'amount', 'payment_method', 'payment_date', 'created_at']
    list_filter = ['payment_method', 'payment_date', 'created_at']
    search_fields = ['payment_reference', 'invoice__invoice_number', 'transaction_reference']
    ordering = ['-payment_date']
    readonly_fields = ['payment_reference']

admin.site.register(Expense)
admin.site.register(Property)
admin.site.register(Document)
admin.site.register(Lead)
admin.site.register(LeadActivity)
admin.site.register(LeadFunnelEvent)
admin.site.register(DailyActionTemplate)
admin.site.register(DailyExecutionDay)
admin.site.register(DailyActionInstance)
admin.site.register(RevenueObjective)
admin.site.register(RevenueKeyResult)
admin.site.register(TurnaroundPlan)
admin.site.register(TurnaroundAction)
admin.site.register(MarketingCampaign)
admin.site.register(Content)
