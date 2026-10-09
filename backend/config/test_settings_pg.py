"""
The test settings, but on PostgreSQL (the production database) instead of SQLite.

CI runs the suite both ways: SQLite is fast, PostgreSQL also exercises row locking
(concurrent purchases cannot overdraw a wallet) and Postgres-only behaviour such as
``SELECT ... FOR UPDATE`` restrictions. Connection details come from the usual POSTGRES_* variables.
"""
import os

from config.test_settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'bug_bounty_test'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
