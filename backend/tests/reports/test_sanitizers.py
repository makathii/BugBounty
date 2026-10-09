"""
Tests for input sanitization utilities.
"""
import pytest
from django.core.exceptions import ValidationError
from reports.sanitizers import (
    sanitize_html,
    sanitize_text_field,
    validate_no_path_traversal,
    validate_safe_url,
    sanitize_search_query,
)


@pytest.mark.django_db
class TestInputSanitizers:
    """Test input sanitization utilities."""

    def test_sanitize_html_removes_script_tags(self):
        """Test that script tags are removed"""
        dirty = '<p>Safe content</p><script>alert("xss")</script>'
        clean = sanitize_html(dirty)
        assert '<script>' not in clean
        assert '</p><script>' not in clean

    def test_sanitize_html_removes_event_handlers(self):
        """Test that event handlers are removed"""
        dirty = '<img src=x onerror="alert(1)">'
        clean = sanitize_html(dirty)
        assert 'onerror' not in clean
        assert 'alert(1)' not in clean

    def test_sanitize_text_field_strips_html_and_normalizes_whitespace(self):
        """Test text field sanitization"""
        dirty = '   Hello   World   '
        clean_text = sanitize_text_field(dirty)
        assert clean_text == 'Hello World'

    def test_validate_no_path_traversal_raises_error(self):
        """Test path traversal detection raises error"""
        with pytest.raises(ValidationError):
            validate_no_path_traversal('../../../etc/passwd')
        with pytest.raises(ValidationError):
            validate_no_path_traversal('..\\..\\windows\\system32')

    def test_validate_no_path_traversal_returns_basename(self):
        """Test valid filenames pass"""
        assert validate_no_path_traversal('file.txt') == 'file.txt'
        assert validate_no_path_traversal('/path/to/file.txt') == 'file.txt'
        assert validate_no_path_traversal('my-document.pdf') == 'my-document.pdf'

    def test_validate_safe_url_blocks_dangerous_schemes(self):
        """Test dangerous URL schemes are blocked"""
        dangerous_urls = [
            'javascript:alert("xss")',
            'vbscript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            'file:///etc/passwd',
            'ftp://attacker.com/malware.exe',
        ]
        for url in dangerous_urls:
            with pytest.raises(ValidationError):
                validate_safe_url(url)

    def test_sanitize_search_query_limits_length(self):
        """Test search query length limiting"""
        long_query = 'a' * 250
        result = sanitize_search_query(long_query)
        assert len(result) <= 200

    def test_sanitize_search_query_removes_special_chars(self):
        """Test dangerous characters are removed"""
        dirty = 'Hello<script>alert(1)</script>World!@#$%^&*()'
        result = sanitize_search_query(dirty)
        assert '<script>' not in result
        assert 'alert(1)' not in result
        assert '@#$%^&*()' not in result
