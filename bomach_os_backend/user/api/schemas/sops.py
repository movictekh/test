# yourapp/schemas.py
from datetime import datetime
from typing import Optional

from ninja import ModelSchema, Schema

from domains.organization.models.sop import SOP
from domains.people.models.responsibility import Responsibility


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
