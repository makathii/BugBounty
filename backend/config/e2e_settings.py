"""
Settings for the browser end-to-end tests (frontend/e2e) and nothing else.

Everything is the real configuration (PostgreSQL via the usual POSTGRES_* variables, real
middleware, real auth) except the request throttles, which a test run that logs in and clicks
around a lot would otherwise trip.
"""
from config.settings import *  # noqa: F401,F403

DEBUG = False
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
# Some views set their own throttle classes, so emptying the defaults is not enough:
# raise every configured rate as well.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        scope: '100000/min' for scope in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']  # noqa: F405
    },
}
