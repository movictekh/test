from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ninja.pagination import paginate, LimitOffsetPagination
from django.core.exceptions import ValidationError

from services.api.schema.document_schemas import DocumentIn, DocumentOut, DocumentUpdate
from services.api.schema.others import MessageSchema
from services.models.document import Document
from user.utils.perm import require_permission

router = Router(tags=["Documents"])


@router.get("", response=List[DocumentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("documents", "list")
def list_documents(
    request,
    user_id: int = None,
    order_id: int = None,
    property_id: int = None,
    search: str = None,
):
    """List all documents with optional filtering."""
    documents = Document.objects.select_related("order", "property").all()

    if user_id:
        documents = documents.filter(user_id=user_id)
    if order_id:
        documents = documents.filter(order_id=order_id)
    if property_id:
        documents = documents.filter(property_id=property_id)
    if search:
        documents = documents.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    return documents


@router.post("", response={201: DocumentOut, 400: MessageSchema})
@require_permission("documents", "create")
def create_document(request, payload: DocumentIn):
    """Create a new document."""
    try:
        document = Document.objects.create(**payload.dict())
        return 201, document
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/{document_id}", response=DocumentOut)
@require_permission("documents", "view")
def get_document(request, document_id: int):
    """Get a specific document by ID."""
    return get_object_or_404(
        Document.objects.select_related("order", "property"), id=document_id
    )


@router.put(
    "/{document_id}",
    response={200: DocumentOut, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("documents", "update")
def update_document(request, document_id: int, payload: DocumentUpdate):
    """Update an existing document."""
    try:
        document = get_object_or_404(Document, id=document_id)
        for attr, value in payload.dict(exclude_unset=True).items():
            setattr(document, attr, value)
        document.save()
        return 200, document
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/{document_id}",
    response={200: MessageSchema, 400: MessageSchema, 404: MessageSchema},
)
@require_permission("documents", "delete")
def delete_document(request, document_id: int):
    """Delete a document."""
    try:
        document = get_object_or_404(Document, id=document_id)
        document.delete()
        return 200, {"detail": "Document deleted successfully"}
    except ValidationError as e:
        return 400, {"detail": e.messages[0]}
    except Exception as e:
        return 400, {"detail": str(e)}


@router.get("/user/{user_id}/documents", response=List[DocumentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("documents", "list")
def get_user_documents(request, user_id: int):
    """Get all documents for a specific user."""
    documents = Document.objects.filter(user_id=user_id).select_related(
        "order", "property"
    )
    return documents


@router.get("/order/{order_id}/documents", response=List[DocumentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("documents", "list")
def get_order_documents(request, order_id: int):
    """Get all documents for a specific order."""
    documents = Document.objects.filter(order_id=order_id).select_related(
        "order", "property"
    )
    return documents


@router.get("/property/{property_id}/documents", response=List[DocumentOut])
@paginate(LimitOffsetPagination, page_size=10)
@require_permission("documents", "list")
def get_property_documents(request, property_id: int):
    """Get all documents for a specific property."""
    documents = Document.objects.filter(property_id=property_id).select_related(
        "order", "property"
    )
    return documents
