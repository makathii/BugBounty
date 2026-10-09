import logging

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


def verify_recaptcha(token: str, remote_ip: str | None = None):
    """
    Validate Google reCAPTCHA v2 token with Google's API.
    Raises ValidationError if invalid.
    If RECAPTCHA_SECRET_KEY is empty, this becomes a no-op (handy for local dev).
    """
    secret = getattr(settings, "RECAPTCHA_SECRET_KEY", "") or ""
    if not secret:
        return

    if not token:
        raise ValidationError("Captcha is required.")

    data = {
        "secret": secret,
        "response": token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        resp = requests.post(settings.RECAPTCHA_VERIFY_URL, data=data, timeout=5)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        raise ValidationError("Captcha verification failed, please try again.")

    if not payload.get("success"):
        # e.g. ['invalid-input-secret'] / ['invalid-keys-or-key-mismatch'] when the site key the
        # frontend uses and RECAPTCHA_SECRET_KEY do not belong to the same reCAPTCHA pair.
        logger.warning("reCAPTCHA rejected the token: %s", payload.get("error-codes"))
        raise ValidationError("Invalid captcha, please try again.")