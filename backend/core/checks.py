"""Deploy-time checks (``manage.py check --deploy``): catch an email setup that would silently
send nothing, or send links that point at localhost."""
from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def email_is_ready_for_production(app_configs, **kwargs):
    problems = []
    if not settings.EMAIL_BACKEND.endswith("smtp.EmailBackend"):
        problems.append(Warning(
            "Emails are not sent over SMTP.",
            hint="Set EMAIL_BACKEND=smtp and the EMAIL_* variables (docs/EMAIL.md). Without it, "
                 "verification and password-reset emails never reach anyone.",
            id="bugbounty.W001",
        ))
    else:
        if getattr(settings, "EMAIL_HOST", "") in ("", "localhost", "127.0.0.1", "mailpit"):
            problems.append(Warning(
                f"EMAIL_HOST is {settings.EMAIL_HOST!r}, a local test server.",
                hint="Point EMAIL_HOST at your mail provider.", id="bugbounty.W002",
            ))
        if not getattr(settings, "EMAIL_HOST_USER", ""):
            problems.append(Warning(
                "EMAIL_HOST_USER is empty; most providers reject unauthenticated mail.",
                hint="Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD.", id="bugbounty.W003",
            ))
    if settings.DEFAULT_FROM_EMAIL.endswith((".local", ".example", ".test")):
        problems.append(Warning(
            f"DEFAULT_FROM_EMAIL is {settings.DEFAULT_FROM_EMAIL!r}, which providers will refuse.",
            hint="Use an address on a domain you have verified with the provider (SPF/DKIM).",
            id="bugbounty.W004",
        ))
    if "localhost" in settings.FRONTEND_URL or "127.0.0.1" in settings.FRONTEND_URL:
        problems.append(Warning(
            f"FRONTEND_URL is {settings.FRONTEND_URL!r}; every link in an email would point at localhost.",
            hint="Set FRONTEND_URL to the public address of the website.", id="bugbounty.W005",
        ))
    return problems
