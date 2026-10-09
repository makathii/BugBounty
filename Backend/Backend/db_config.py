"""
Database / cache configuration built from environment variables.

Kept out of settings.py so it can be unit-tested without importing settings.
Precedence for the database: DATABASE_URL > POSTGRES_* variables > the
historical docker-compose defaults (host ``db``, ``postgres``/``postgres``).
"""
from urllib.parse import parse_qs, unquote, urlparse


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_database_url(url):
    """Parse ``postgres://user:pass@host:port/name?opt=val`` into a Django config."""
    parsed = urlparse(url)
    if parsed.scheme not in ('postgres', 'postgresql', 'pgsql'):
        raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme!r}")
    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parsed.path.lstrip('/')),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or ''),
    }
    options = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
    if options:
        config['OPTIONS'] = options
    return config


def build_databases(env):
    """
    Return the ``DATABASES`` setting.

    ``DB_CONN_MAX_AGE`` (seconds, default 60) enables persistent connections so
    each request does not pay a TCP+auth handshake; set 0 to disable, e.g. when
    a transaction-mode pooler such as PgBouncer sits in front (then also set
    ``DB_DISABLE_SERVER_SIDE_CURSORS=True``). Connections are health-checked
    before reuse.
    """
    url = env.get('DATABASE_URL')
    if url:
        default = parse_database_url(url)
    else:
        default = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.get('POSTGRES_DB', 'bug_bounty_db'),
            'USER': env.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': env.get('POSTGRES_PASSWORD', 'postgres'),
            'HOST': env.get('POSTGRES_HOST', 'db'),
            'PORT': env.get('POSTGRES_PORT', '5432'),
        }
    default['CONN_MAX_AGE'] = _int(env.get('DB_CONN_MAX_AGE'), 60)
    default['CONN_HEALTH_CHECKS'] = True
    if env.get('DB_DISABLE_SERVER_SIDE_CURSORS', 'False') == 'True':
        default['DISABLE_SERVER_SIDE_CURSORS'] = True
    return {'default': default}


def build_caches(env):
    """
    Shared Redis cache when ``REDIS_URL`` is set, otherwise Django's default
    per-process in-memory cache. Throttle counters and the leaderboard cache
    only behave correctly across several workers with the shared backend.
    """
    url = env.get('REDIS_URL')
    if not url:
        return {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    return {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': url,
            'KEY_PREFIX': env.get('CACHE_KEY_PREFIX', 'bugbounty'),
        }
    }
