import mimetypes
import os
import uuid
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from ninja import File, Router
from ninja.files import UploadedFile

from user.api.schemas.others import FileUploadResponseSchema, MessageSchema
from user.utils.compress_file import compress_image

orthers_api = Router(tags=["Others"])


@orthers_api.post(
    "/upload-file",
    response={200: FileUploadResponseSchema, 400: MessageSchema},
    tags=["Upload"],
)
def upload_file(request, file: UploadedFile = File(...)):
    mime_type, _ = mimetypes.guess_type(file.name)

    if mime_type and not mime_type.startswith("image/"):
        unique_name = f"{uuid.uuid4()}-{file.name}"
        content = ContentFile(file.read())
        try:
            file_name = default_storage.save(unique_name, content)
            file_url = default_storage.url(file_name)
        except Exception:
            local_storage = FileSystemStorage(
                location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL
            )
            file_name = local_storage.save(unique_name, content)
            file_url = local_storage.url(file_name)
        if file_url.startswith("/"):
            file_url = request.build_absolute_uri(file_url)
        return {"url": file_url}

    file_url = compress_image(file)
    if file_url.startswith("/"):
        file_url = request.build_absolute_uri(file_url)

    return {"url": file_url}
