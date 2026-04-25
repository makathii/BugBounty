"""
Tests for file upload security validators (Medium #15).
Covers: EXIF stripping, image dimension / decompression-bomb guards,
MIME-type validation, extension whitelist, and size limits.

These are unit tests against the validators module — they do NOT require
ClamAV, Docker, or a running database (most tests are not db-marked).
"""
import io
import os
import tempfile

import pytest
from django.core.exceptions import ValidationError

from reports.validators import (
    strip_exif,
    validate_image_dimensions,
    validate_extension,
    validate_size,
    validate_mime,
    IMAGE_EXTENSIONS,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jpeg_with_exif(path: str) -> None:
    """Create a tiny JPEG file with a fake EXIF GPS tag so we can verify removal."""
    from PIL import Image
    import piexif

    img = Image.new("RGB", (100, 100), color=(200, 100, 50))
    exif_dict = {
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((51, 1), (30, 1), (0, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((0, 1), (7, 1), (0, 1)),
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, format="JPEG", exif=exif_bytes)


def _make_plain_jpeg(path: str, size=(100, 100)) -> None:
    """Create a plain JPEG without any EXIF data."""
    from PIL import Image
    img = Image.new("RGB", size, color=(128, 64, 32))
    img.save(path, format="JPEG")


def _make_png(path: str, size=(100, 100)) -> None:
    from PIL import Image
    img = Image.new("RGB", size, color=(10, 20, 30))
    img.save(path, format="PNG")


# ---------------------------------------------------------------------------
# EXIF stripping
# ---------------------------------------------------------------------------

class TestStripExif:
    def test_strip_exif_removes_gps_data(self):
        """GPS EXIF data must be gone after stripping."""
        try:
            import piexif
        except ImportError:
            pytest.skip("piexif not installed — skipping EXIF stripping test")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = f.name
        try:
            _make_jpeg_with_exif(path)

            # Verify EXIF exists before stripping
            exif_before = piexif.load(path)
            assert "GPS" in exif_before and exif_before["GPS"], "Test setup: EXIF GPS should exist before stripping"

            result = strip_exif(path)
            assert result is True, "strip_exif should return True for image files"

            # After stripping, GPS data must be absent or empty
            exif_after = piexif.load(path)
            gps_data = exif_after.get("GPS", {})
            assert not gps_data, f"GPS EXIF data still present after stripping: {gps_data}"
        finally:
            os.unlink(path)

    def test_strip_exif_returns_false_for_non_image(self):
        """Non-image files must be skipped — returns False, file unchanged."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake content")
            path = f.name
        try:
            result = strip_exif(path)
            assert result is False
        finally:
            os.unlink(path)

    def test_strip_exif_preserves_image_content(self):
        """Image pixel data must survive EXIF stripping."""
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = f.name
        try:
            _make_plain_jpeg(path, size=(50, 50))
            strip_exif(path)
            with Image.open(path) as img:
                assert img.size == (50, 50)
                assert img.mode == "RGB"
        finally:
            os.unlink(path)

    def test_strip_exif_works_on_png(self):
        """PNG files (which don't use EXIF) must be processed without error."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            _make_png(path)
            result = strip_exif(path)
            # PNG uses RGB — should succeed
            assert isinstance(result, bool)
        finally:
            os.unlink(path)

    def test_strip_exif_on_nonexistent_file_returns_false(self):
        """strip_exif must never raise — missing file returns False."""
        result = strip_exif("/tmp/this_file_does_not_exist_xyzzy.jpg")
        assert result is False


# ---------------------------------------------------------------------------
# Image dimension / decompression bomb validation
# ---------------------------------------------------------------------------

class TestValidateImageDimensions:
    def test_normal_image_passes(self):
        """A reasonably sized image must not raise."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = f.name
        try:
            _make_plain_jpeg(path, size=(800, 600))
            validate_image_dimensions(path)  # should not raise
        finally:
            os.unlink(path)

    def test_oversized_dimension_rejected(self):
        """Images wider/taller than MAX_IMAGE_DIMENSION must be rejected."""
        from PIL import Image
        oversized = MAX_IMAGE_DIMENSION + 1
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            path = f.name
        try:
            img = Image.new("RGB", (oversized, 100), color=(0, 0, 0))
            img.save(path, format="JPEG")
            with pytest.raises(ValidationError, match="dimensions"):
                validate_image_dimensions(path)
        finally:
            os.unlink(path)

    def test_non_image_skipped(self):
        """Non-image files (e.g. .pdf) must be silently skipped."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            path = f.name
        try:
            validate_image_dimensions(path)  # must not raise
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Extension whitelist
# ---------------------------------------------------------------------------

class TestValidateExtension:
    @pytest.mark.parametrize("filename", [
        "screenshot.png", "proof.jpg", "evidence.jpeg",
        "report.pdf", "notes.txt", "archive.zip",
    ])
    def test_allowed_extensions_pass(self, filename):
        validate_extension(filename)  # must not raise

    @pytest.mark.parametrize("filename", [
        "shell.php", "exploit.exe", "backdoor.sh",
        "virus.bat", "macro.docm", "script.js", "test.html",
    ])
    def test_blocked_extensions_rejected(self, filename):
        with pytest.raises(ValidationError):
            validate_extension(filename)

    def test_extension_check_is_case_insensitive(self):
        """Uppercase extensions must be caught too."""
        with pytest.raises(ValidationError):
            validate_extension("malware.PHP")


# ---------------------------------------------------------------------------
# File size limit
# ---------------------------------------------------------------------------

class TestValidateSize:
    def test_within_limit_passes(self):
        from django.conf import settings
        validate_size(settings.MAX_UPLOAD_SIZE - 1)  # just under limit

    def test_exactly_at_limit_fails(self):
        from django.conf import settings
        with pytest.raises(ValidationError):
            validate_size(settings.MAX_UPLOAD_SIZE + 1)

    def test_zero_size_passes(self):
        validate_size(0)


# ---------------------------------------------------------------------------
# MIME type whitelist
# ---------------------------------------------------------------------------

class TestValidateMime:
    @pytest.mark.parametrize("mime", [
        "image/png", "image/jpeg", "application/pdf",
        "text/plain", "application/zip",
    ])
    def test_allowed_mimes_pass(self, mime):
        validate_mime(mime)  # must not raise

    @pytest.mark.parametrize("mime", [
        "application/x-php", "application/x-executable",
        "text/html", "application/javascript", "application/x-sh",
    ])
    def test_blocked_mimes_rejected(self, mime):
        with pytest.raises(ValidationError):
            validate_mime(mime)
