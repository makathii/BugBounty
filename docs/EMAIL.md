# Email

The platform sends email for: verifying an address, password resets, report decisions, new comments,
program invitations and new report notices. Every one of these is also an in-app notification
(the bell in the navbar), so a missed email never means a missed event.

## Local development

Nothing to set up. `docker-compose` starts **Mailpit**; every email lands in its inbox at
<http://localhost:8025>. Nothing ever leaves your machine.

## Production

Use any SMTP provider (SendGrid, Mailgun, Postmark, Amazon SES, your own server). Set, for example:

```
EMAIL_BACKEND=smtp
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True          # port 587 = STARTTLS. For port 465 use EMAIL_USE_SSL=True instead.
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<provider key>
DEFAULT_FROM_EMAIL=BugBounty <no-reply@your-domain.example>
FRONTEND_URL=https://app.your-domain.example     # used for every link inside an email
BACKEND_PUBLIC_URL=https://api.your-domain.example
EMAIL_TIMEOUT=10            # seconds; a stuck mail server must not hang a request or worker
```

### Before you go live

1. **Verify the sender domain** with the provider and publish its **SPF** and **DKIM** DNS records
   (and a DMARC policy). Without them most mail lands in spam or is refused.
2. **Run the deploy check.** It flags the settings that silently break email:
   ```
   python manage.py check --deploy
   ```
   `bugbounty.W001`–`W005` mean: not using SMTP, EMAIL_HOST still local, no SMTP login, a placeholder
   sender address, or `FRONTEND_URL` still pointing at localhost.
3. **Send a real test email** from the production environment:
   ```
   python manage.py send_test_email you@your-domain.example
   ```
   It prints the backend, host and sender it used, and fails loudly with the SMTP error if the
   provider refuses.
4. **Run Celery with a broker** (Redis). Without one, emails are sent inline during the request; with
   one they are sent by the worker, retried with back-off up to 5 times, and a mail outage never
   fails the action that triggered it.

### Privacy

Comment notifications are sent one message per recipient, so researchers and companies never see
each other's addresses.

### What this setup has and has not been tested with

Automated tests cover the settings, the deploy checks, the test command and every notification
path using Django's in-memory mail backend; browser tests read emails from a file backend. Delivery
through a real provider cannot be tested in CI: do step 3 once per environment.
