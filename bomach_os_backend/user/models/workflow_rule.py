from django.db import models

from user.models.base import BaseModel


class WorkflowRule(BaseModel):
    """
    Defines an automation rule: trigger → conditions → action.
    When a trigger event fires, conditions are evaluated against the
    object instance. If all conditions match, the action is executed.
    """

    TRIGGER_CHOICES = [
        ('service_order_status_changed', 'Service Order Status Changed'),
        ('quote_status_changed', 'Quote Status Changed'),
    ]

    ACTION_CHOICES = [
        ('send_notification', 'Send Notification'),
    ]

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    trigger_event = models.CharField(max_length=50, choices=TRIGGER_CHOICES)

    # Conditions stored as JSON list: [{"field": "order_status", "operator": "eq", "value": "completed"}]
    # All conditions must match (AND logic).
    conditions = models.JSONField(default=list, blank=True)

    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    # Action config: e.g. {"recipient_ids": [1, 2], "title": "Order Completed", "message": "..."}
    action_config = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflow_rules_created',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_trigger_event_display()})"


class WorkflowRuleLog(BaseModel):
    """
    Audit log of workflow rule executions.
    """

    rule = models.ForeignKey(
        WorkflowRule,
        on_delete=models.CASCADE,
        related_name='execution_logs',
    )
    trigger_event = models.CharField(max_length=50)
    trigger_object_id = models.PositiveIntegerField()
    trigger_object_type = models.CharField(max_length=100)
    conditions_met = models.BooleanField(default=False)
    action_executed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = "executed" if self.action_executed else "skipped"
        return f"[{status}] {self.rule.name} → {self.trigger_object_type}#{self.trigger_object_id}"
