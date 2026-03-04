import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

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
        raise ValidationError("Invalid captcha, please try again.")