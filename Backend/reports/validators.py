import os
from django.conf import settings
from django.core.exceptions import ValidationError

def validate_extension(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(f"Forbidden file extension: {ext}")

def detect_mime(path: str) -> str:
    try:
        import magic 
        return magic.Magic(mime=True).from_file(path)
    except Exception:
        try:
            import filetype
            kind = filetype.guess(path)
            return kind.mime if kind else "application/octet-stream"
        except Exception:
            return "application/octet-stream"

def validate_mime(mime: str):
    if mime not in settings.ALLOWED_MIME_TYPES:
        raise ValidationError(f"Forbidden MIME type: {mime}")

def validate_size(size: int):
    if size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(f"File too large (>{settings.MAX_UPLOAD_SIZE} bytes)")