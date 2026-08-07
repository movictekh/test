
from ninja import UploadedFile
from io import BytesIO
from PIL import Image
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def compress_image(file: UploadedFile):    
    # Open image with Pillow
    file_content = file.read()

    image = Image.open(BytesIO(file_content))
    
    # Convert RGBA to RGB if necessary (for JPEG compatibility)
    if image.mode in ('RGBA', 'LA', 'P'):
        # Create a white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    
    # Resize image if too large (optional)
    max_size = (1920, 1080)  # Adjust as needed
    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Compress and save to BytesIO
    output = BytesIO()
    
    # Determine format and quality based on original file
    file_extension = file.name.lower().split('.')[-1] if '.' in file.name else 'jpg'
    
    if file_extension in ['jpg', 'jpeg']:
        image.save(output, format='JPEG', quality=85, optimize=True)
        content_type = 'image/jpeg'
    elif file_extension == 'png':
        image.save(output, format='PNG', optimize=True)
        content_type = 'image/png'
    elif file_extension == 'webp':
        image.save(output, format='WEBP', quality=85, optimize=True)
        content_type = 'image/webp'
    else:
        # Default to JPEG for other formats
        image.save(output, format='JPEG', quality=85, optimize=True)
        content_type = 'image/jpeg'
        file_extension = 'jpg'
    
    # Get compressed image data
    compressed_data = output.getvalue()
    output.close()
    
    # Generate unique filename with proper extension
    unique_name = f"{uuid.uuid4()}.{file_extension}"
    
    # Save compressed image
    file_name = default_storage.save(unique_name, ContentFile(compressed_data))
    file_url = default_storage.url(file_name)
    return file_url
