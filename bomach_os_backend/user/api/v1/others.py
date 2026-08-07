from ninja import Router, File
from ninja.files import UploadedFile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.conf import settings
from typing import Optional
import os
import uuid

from user.api.schemas.others import FileUploadResponseSchema, MessageSchema
from user.utils.compress_file import compress_image
import mimetypes


orthers_api = Router(tags=["Others"])

@orthers_api.post(
    "/upload-file",
    response={200: FileUploadResponseSchema, 400: MessageSchema},
    tags=["Upload"]
)
def upload_file(request, file: UploadedFile = File(...)):
    mime_type, _ = mimetypes.guess_type(file.name)
    
    if mime_type and not mime_type.startswith("image/"):
        unique_name = f"{uuid.uuid4()}-{file.name}"

        file_name = default_storage.save(unique_name, ContentFile(file.read()))
        file_url = default_storage.url(file_name)
        return {"url": file_url}
    
    file_url = compress_image(file)

    return {"url": file_url}
