from ninja import Schema

class MessageSchema(Schema):
    """Schema for success/error messages"""
    detail: str
