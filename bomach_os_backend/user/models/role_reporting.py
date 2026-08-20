from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from user.models.base import BaseModel


class RoleReportingLine(BaseModel):
    class RelationshipType(models.TextChoices):
        DIRECT = "direct", "Direct"
        DOTTED_LINE = "dotted_line", "Dotted Line"
        ESCALATION = "escalation", "Escalation"

    role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="reporting_lines",
    )
    reports_to_role = models.ForeignKey(
        "Role",
        on_delete=models.CASCADE,
        related_name="reporting_lines_to",
    )
    relationship_type = models.CharField(
        max_length=30,
        choices=RelationshipType.choices,
        default=RelationshipType.DIRECT,
    )
    branch = models.ForeignKey(
        "Branch",
        on_delete=models.CASCADE,
        related_name="role_reporting_lines",
        null=True,
        blank=True,
    )
    department = models.ForeignKey(
        "Department",
        on_delete=models.CASCADE,
        related_name="role_reporting_lines",
        null=True,
        blank=True,
    )
    unit = models.ForeignKey(
        "Unit",
        on_delete=models.CASCADE,
        related_name="role_reporting_lines",
        null=True,
        blank=True,
    )
    sequence = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        indexes = [
            models.Index(fields=["role", "sequence"]),
            models.Index(fields=["role", "relationship_type", "is_active"]),
            models.Index(fields=["role", "reports_to_role"]),
            models.Index(fields=["branch", "department", "unit"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "role",
                    "reports_to_role",
                    "relationship_type",
                    "branch",
                    "department",
                    "unit",
                ],
                name="uniq_role_reporting_line_edge",
            )
        ]

    def clean(self):
        if (
            self.role_id
            and self.reports_to_role_id
            and self.role_id == self.reports_to_role_id
        ):
            raise ValidationError(
                {"reports_to_role": "A role cannot report to itself."}
            )

        self._validate_unit_department()
        self._validate_duplicate_active_line()
        self._validate_direct_line_cycle()

    def _scope_filter(self):
        return {
            "branch_id": self.branch_id,
            "department_id": self.department_id,
            "unit_id": self.unit_id,
        }

    def _validate_unit_department(self):
        if (
            self.unit_id
            and self.department_id
            and self.unit.department_id != self.department_id
        ):
            raise ValidationError(
                {"unit": "Unit must belong to the selected department."}
            )

    def _validate_duplicate_active_line(self):
        if not self.is_active or not self.role_id or not self.reports_to_role_id:
            return

        duplicate = RoleReportingLine.objects.filter(
            role_id=self.role_id,
            reports_to_role_id=self.reports_to_role_id,
            relationship_type=self.relationship_type,
            is_active=True,
            **self._scope_filter(),
        )
        if self.pk:
            duplicate = duplicate.exclude(pk=self.pk)
        if duplicate.exists():
            raise ValidationError(
                "An active reporting line with this scope already exists."
            )

        if self.relationship_type != self.RelationshipType.DIRECT:
            return

        active_direct = RoleReportingLine.objects.filter(
            role_id=self.role_id,
            relationship_type=self.RelationshipType.DIRECT,
            is_active=True,
            **self._scope_filter(),
        )
        if self.pk:
            active_direct = active_direct.exclude(pk=self.pk)
        if active_direct.exists():
            raise ValidationError(
                "A role can only have one active direct reporting line per scope."
            )

    def _validate_direct_line_cycle(self):
        if (
            not self.is_active
            or self.relationship_type != self.RelationshipType.DIRECT
            or not self.role_id
            or not self.reports_to_role_id
        ):
            return

        current_role_id = self.reports_to_role_id
        visited_role_ids = {self.role_id}
        while current_role_id:
            if current_role_id in visited_role_ids:
                raise ValidationError("Direct reporting lines cannot create a cycle.")
            visited_role_ids.add(current_role_id)

            next_line = (
                RoleReportingLine.objects.filter(
                    role_id=current_role_id,
                    relationship_type=self.RelationshipType.DIRECT,
                    is_active=True,
                    **self._scope_filter(),
                )
                .exclude(pk=self.pk)
                .order_by("sequence", "id")
                .first()
            )
            current_role_id = next_line.reports_to_role_id if next_line else None

    def __str__(self):
        return f"{self.role.name} -> {self.reports_to_role.name} ({self.relationship_type})"
