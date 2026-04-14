"""
Tests for file upload security.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from .validators import validate_extension, validate_size, validate_mime
from .models_attachment import Attachment


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
        from .validators import detect_mime
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
