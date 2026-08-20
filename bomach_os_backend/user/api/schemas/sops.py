# yourapp/schemas.py
from ninja import ModelSchema, Schema
from typing import Optional
from datetime import datetime
from user.models import SOP, Responsibility  # adjust imports as needed


class SOPIn(ModelSchema):
    class Meta:
        model = SOP
        fields = ["title", "description", "version", "priority", "is_up_to_date"]


class SOPOut(ModelSchema):
    class Meta:
        model = SOP
        fields = [
            "id",
            "title",
            "description",
            "version",
            "priority",
            "is_up_to_date",
            "created_at",
            "updated_at",
        ]


class ResponsibilityIn(ModelSchema):
    class Meta:
        model = Responsibility
        fields = ["title", "description", "priority", "frequency", "kpi_target"]


class ResponsibilityOut(ModelSchema):
    class Meta:
        model = Responsibility
        fields = [
            "id",
            "title",
            "description",
            "priority",
            "frequency",
            "kpi_target",
            "created_at",
            "updated_at",
        ]


class MessageOut(Schema):
    message: str
