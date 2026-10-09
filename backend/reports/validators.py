import os
from django.conf import settings
from django.core.exceptions import ValidationError

# Maximum pixel dimension for either axis — anything larger is suspicious
MAX_IMAGE_DIMENSION = getattr(settings, 'MAX_IMAGE_DIMENSION', 8000)
# Maximum uncompressed pixel count (~30 MP) — guards against decompression bombs
MAX_IMAGE_PIXELS = getattr(settings, 'MAX_IMAGE_PIXELS', 30_000_000)

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


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


def validate_image_dimensions(path: str):
    """
    Reject images whose dimensions could cause a decompression bomb
    or serve as a vector for DoS via memory exhaustion during processing.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return  # Only applies to image files

    try:
        from PIL import Image
        # Set PIL's decompression bomb limit (raises DecompressionBombError)
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

        with Image.open(path) as img:
            width, height = img.size

        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            raise ValidationError(
                f"Image dimensions ({width}×{height}) exceed the maximum allowed "
                f"({MAX_IMAGE_DIMENSION}×{MAX_IMAGE_DIMENSION})."
            )
        if width * height > MAX_IMAGE_PIXELS:
            raise ValidationError(
                f"Image pixel count ({width * height:,}) exceeds the maximum "
                f"allowed ({MAX_IMAGE_PIXELS:,})."
            )
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Could not verify image dimensions: {e}")


def strip_exif(path: str) -> bool:
    """
    Remove all EXIF metadata from an image to prevent location/device disclosure.
    Operates in-place. Returns True if stripping was performed, False if skipped.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return False

    try:
        from PIL import Image

        with Image.open(path) as img:
            # Convert to RGB if necessary (e.g. RGBA PNGs or palette images)
            mode = img.mode
            if mode not in ('RGB', 'RGBA', 'L', 'P'):
                return False

            # Rebuild image data without the EXIF segment
            image_data = list(img.getdata())
            clean_img = Image.new(mode, img.size)
            clean_img.putdata(image_data)

        clean_img.save(path)
        return True
    except Exception:
        # Never fail a file upload just because EXIF stripping errored —
        # log it in production but don't reject the file.
        return False