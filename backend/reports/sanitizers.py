"""
Input sanitization utilities for BugBounty platform.
"""
import bleach
from django.core.exceptions import ValidationError
import re


def sanitize_html(value, allowed_tags=None):
    """
    Sanitize HTML content to prevent XSS.
    By default, strips all HTML tags.
    """
    if not value:
        return value

    if allowed_tags is None:
        allowed_tags = []  # Strip all HTML by default

    allowed_attributes = {}
    allowed_protocols = ['http', 'https', 'mailto']

    return bleach.clean(
        value,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=allowed_protocols,
        strip=True
    )


def sanitize_text_field(value, max_length=None):
    """
    Sanitize text fields - removes HTML and normalizes whitespace.
    """
    if not value:
        return value

    # Strip HTML
    cleaned = bleach.clean(value, tags=[], strip=True)

    # Normalize whitespace
    cleaned = ' '.join(cleaned.split())

    # Check length
    if max_length and len(cleaned) > max_length:
        raise ValidationError(f"Text exceeds maximum length of {max_length} characters.")

    return cleaned


def validate_no_path_traversal(filename):
    """
    Validate filename doesn't contain path traversal sequences.
    """
    if not filename:
        return filename

    # Check for path traversal patterns
    dangerous_patterns = [
        '..',
        '../',
        '..\\',
        '/..',
        '\\..',
        '~',
        '/etc/',
        '/proc/',
        '/sys/',
        'C:\\',
        '\\windows\\',
    ]

    for pattern in dangerous_patterns:
        if pattern in filename:
            raise ValidationError(f"Invalid filename: contains dangerous pattern '{pattern}'")

    # Normalize and return basename only
    import os
    return os.path.basename(filename)


def validate_safe_url(url):
    """
    Validate URL is safe (no javascript:, data:, etc).
    """
    if not url:
        return url

    dangerous_schemes = [
        'javascript:',
        'vbscript:',
        'data:',
        'file:',
        'ftp:',
        'chrome:',
        'about:',
    ]

    url_lower = url.lower().strip()

    for scheme in dangerous_schemes:
        if url_lower.startswith(scheme):
            raise ValidationError(f"URL uses unsafe scheme: {scheme}")

    return url


def sanitize_search_query(query):
    """
    Sanitize search queries to prevent SQL injection and XSS.
    """
    if not query:
        return query

    # Remove potentially dangerous characters
    # Keep alphanumeric, spaces, and basic punctuation
    cleaned = re.sub(r'[^\w\s\-\.@]', '', query)

    # Limit length
    if len(cleaned) > 200:
        cleaned = cleaned[:200]

    return cleaned.strip()


def validate_json_safe(value):
    """
    Validate that a value is safe to serialize to JSON.
    Prevents prototype pollution-style attacks.
    """
    if isinstance(value, dict):
        dangerous_keys = ['__proto__', 'constructor', 'prototype']
        for key in value.keys():
            if key in dangerous_keys:
                raise ValidationError(f"Dangerous key in JSON: {key}")
            validate_json_safe(value[key])
    elif isinstance(value, list):
        for item in value:
            validate_json_safe(item)

    return value
