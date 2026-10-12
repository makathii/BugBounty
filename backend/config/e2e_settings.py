"""
Settings for the browser end-to-end tests (frontend/e2e) and nothing else.

Everything is the real configuration (PostgreSQL via the usual POSTGRES_* variables, real
middleware, real auth) except the request throttles, which a test run that logs in and clicks
around a lot would otherwise trip.
"""
import os

from config.settings import *  # noqa: F401,F403

DEBUG = False
# Django's dev server starts a thread per request and each would keep its own database connection
# for CONN_MAX_AGE seconds; a long browser run then exhausts PostgreSQL's connection limit.
DATABASES['default']['CONN_MAX_AGE'] = 0  # noqa: F405
# Emails are written to files so the browser tests (a different process) can read the
# verification and password-reset links the app sends.
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.environ.get('E2E_MAIL_DIR', '/tmp/bugbounty-e2e-mail')
# Some views set their own throttle classes, so emptying the defaults is not enough:
# raise every configured rate as well.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        scope: '100000/min' for scope in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']  # noqa: F405
    },
}
