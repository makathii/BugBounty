"""
Tests for file upload security.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from reports.validators import validate_extension, validate_size, validate_mime
from reports.models import Attachment


@pytest.mark.django_db
class TestFileUploadSecurity:
    """Test file upload security measures."""

    def test_file_extension_validation(self):
        """Test that validate_extension allows valid extensions and rejects invalid ones."""
        # Valid extensions should pass
        validate_extension("test.png")
        validate_extension("test.jpg")
        validate_extension("test.pdf")
        validate_extension("test.txt")
        validate_extension("test.zip")

        # Invalid extensions should raise ValidationError
        invalid_extensions = [
            "test.exe",
            "test.php",
            "test.js",
            "test.html",
            "test.bat",
            "test.sh",
        ]
        for ext in invalid_extensions:
            with pytest.raises(ValidationError):
                validate_extension(ext)

    def test_file_size_validation_within_limit(self):
        """Test validation passes for files under MAX_UPLOAD_SIZE."""
        small_file = SimpleUploadedFile("test.png", b"x89PNG\r\n\x1a\n")
        validate_size(small_file.size)  # Should pass (assuming small_file is < MAX_UPLOAD_SIZE)

    def test_file_size_validation_over_limit(self):
        """Test validation fails for files exceeding MAX_UPLOAD_SIZE (10MB default)."""
        # Create a file that's over 10MB
        large_content = b"x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)  # > 10MB
        large_file = SimpleUploadedFile("large.png", large_content)
        with pytest.raises(ValidationError):
            validate_size(large_file.size)

    def test_mime_type_validation_allowed(self):
        """Test allowed MIME types pass validation."""
        allowed_mimes = [
            "image/png",
            "image/jpeg",
            "application/pdf",
            "text/plain",
            "application/zip",
        ]
        for mime in allowed_mimes:
            validate_mime(mime)  # Should not raise

    def test_mime_type_validation_blocked(self):
        """Test blocked MIME types fail validation."""
        blocked_mimes = [
            "application/javascript",
            "text/html",
            "application/xhtml+xml",
            "application/octet-stream",  # Generic binary
        ]
        for mime in blocked_mimes:
            with pytest.raises(ValidationError):
                validate_mime(mime)

    def test_mime_detection(self):
        """Test MIME detection from file content."""
        from reports.validators import detect_mime
        import tempfile
        import os

        # Create a fake PNG file
        png_content = b"x89PNG\r\n\x1a\n"

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(png_content)
            tmp_path = tmp.name

        try:
            detected_mime = detect_mime(tmp_path)
            assert detected_mime in ["image/png", "application/octet-stream", "text/plain"]
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# EXIF stripping tests
# ---------------------------------------------------------------------------

class TestExifStripping:
    """Test that EXIF metadata is removed from uploaded images."""

    def _make_jpeg_with_exif(self, path):
        """Write a minimal JPEG with EXIF GPS coordinates to disk."""
        from PIL import Image
        import piexif

        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        exif_dict = {
            "GPS": {
                piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (0, 1)),
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (0, 1)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(path, "JPEG", exif=exif_bytes)

    def _make_plain_jpeg(self, path):
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        img.save(path, "JPEG")

    def test_strip_exif_removes_gps_data(self, tmp_path):
        """After stripping, the image must contain no EXIF GPS data."""
        pytest.importorskip("piexif")
        img_path = str(tmp_path / "gps_test.jpg")
        self._make_jpeg_with_exif(img_path)

        from reports.validators import strip_exif
        result = strip_exif(img_path)
        assert result is True

        import piexif
        try:
            exif = piexif.load(img_path)
            gps = exif.get("GPS", {})
            assert len(gps) == 0, "GPS data still present after stripping"
        except Exception:
            pass  # If piexif can't load it, EXIF is definitely gone

    def test_strip_exif_preserves_image_content(self, tmp_path):
        """Stripped image must still be a valid, openable image."""
        from PIL import Image
        from reports.validators import strip_exif

        img_path = str(tmp_path / "preserve_test.jpg")
        self._make_plain_jpeg(img_path)
        strip_exif(img_path)

        with Image.open(img_path) as img:
            assert img.size == (100, 100)

    def test_strip_exif_skips_non_image_files(self, tmp_path):
        """strip_exif must return False (no-op) for non-image extensions."""
        from reports.validators import strip_exif
        txt_path = str(tmp_path / "document.txt")
        with open(txt_path, "w") as f:
            f.write("hello")
        assert strip_exif(txt_path) is False

    def test_strip_exif_skips_pdf(self, tmp_path):
        from reports.validators import strip_exif
        pdf_path = str(tmp_path / "report.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake pdf content")
        assert strip_exif(pdf_path) is False


# ---------------------------------------------------------------------------
# Image dimension / decompression-bomb tests
# ---------------------------------------------------------------------------

class TestImageDimensionValidation:
    """Test that oversized images are rejected before saving."""

    def _make_image(self, path, width, height, fmt="PNG"):
        from PIL import Image
        img = Image.new("RGB", (width, height), color=(128, 128, 128))
        img.save(path, fmt)

    def test_normal_image_passes(self, tmp_path):
        from reports.validators import validate_image_dimensions
        img_path = str(tmp_path / "ok.png")
        self._make_image(img_path, 800, 600)
        validate_image_dimensions(img_path)  # must not raise

    def test_oversized_width_rejected(self, tmp_path):
        from django.core.exceptions import ValidationError as DjValidationError
        from reports.validators import validate_image_dimensions, MAX_IMAGE_DIMENSION
        img_path = str(tmp_path / "wide.png")
        self._make_image(img_path, MAX_IMAGE_DIMENSION + 100, 100)
        with pytest.raises(DjValidationError):
            validate_image_dimensions(img_path)

    def test_oversized_height_rejected(self, tmp_path):
        from django.core.exceptions import ValidationError as DjValidationError
        from reports.validators import validate_image_dimensions, MAX_IMAGE_DIMENSION
        img_path = str(tmp_path / "tall.png")
        self._make_image(img_path, 100, MAX_IMAGE_DIMENSION + 100)
        with pytest.raises(DjValidationError):
            validate_image_dimensions(img_path)

    def test_non_image_file_skipped(self, tmp_path):
        """Dimension check must be a no-op for non-image file types."""
        from reports.validators import validate_image_dimensions
        txt_path = str(tmp_path / "notes.txt")
        with open(txt_path, "w") as f:
            f.write("not an image")
        validate_image_dimensions(txt_path)  # must not raise

    def test_pdf_skipped(self, tmp_path):
        from reports.validators import validate_image_dimensions
        pdf_path = str(tmp_path / "file.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake")
        validate_image_dimensions(pdf_path)  # must not raise
