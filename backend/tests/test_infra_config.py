"""Phase E: env-driven DB/cache config and audit-log retention."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from config.db_config import build_caches, build_databases, parse_database_url
from audit.models import SecurityAuditLog


class TestDatabaseConfig:
    def test_legacy_defaults_preserved(self):
        db = build_databases({})['default']
        assert (db['NAME'], db['USER'], db['PASSWORD'], db['HOST'], db['PORT']) == (
            'bug_bounty_db', 'postgres', 'postgres', 'db', '5432')

    def test_postgres_env_vars_are_honoured(self):
        db = build_databases({'POSTGRES_DB': 'x', 'POSTGRES_USER': 'u',
                              'POSTGRES_PASSWORD': 'p', 'POSTGRES_HOST': 'h'})['default']
        assert (db['NAME'], db['USER'], db['PASSWORD'], db['HOST']) == ('x', 'u', 'p', 'h')

    def test_database_url_wins_and_decodes(self):
        db = build_databases({
            'DATABASE_URL': 'postgres://us%40er:p%3Ass@pg.example:6432/mydb?sslmode=require',
            'POSTGRES_DB': 'ignored',
        })['default']
        assert db['NAME'] == 'mydb' and db['USER'] == 'us@er' and db['PASSWORD'] == 'p:ss'
        assert db['HOST'] == 'pg.example' and db['PORT'] == '6432'
        assert db['OPTIONS'] == {'sslmode': 'require'}

    def test_rejects_non_postgres_url(self):
        with pytest.raises(ValueError):
            parse_database_url('mysql://u:p@h/db')

    def test_persistent_connections_by_default(self):
        db = build_databases({})['default']
        assert db['CONN_MAX_AGE'] == 60 and db['CONN_HEALTH_CHECKS'] is True

    def test_conn_max_age_override_and_pooler_flag(self):
        db = build_databases({'DB_CONN_MAX_AGE': '0',
                              'DB_DISABLE_SERVER_SIDE_CURSORS': 'True'})['default']
        assert db['CONN_MAX_AGE'] == 0 and db['DISABLE_SERVER_SIDE_CURSORS'] is True

    def test_bad_conn_max_age_falls_back(self):
        assert build_databases({'DB_CONN_MAX_AGE': 'abc'})['default']['CONN_MAX_AGE'] == 60


class TestCacheConfig:
    def test_locmem_without_redis_url(self):
        assert build_caches({})['default']['BACKEND'].endswith('LocMemCache')

    def test_redis_when_url_set(self):
        c = build_caches({'REDIS_URL': 'redis://redis:6379/1'})['default']
        assert c['BACKEND'].endswith('RedisCache') and c['LOCATION'] == 'redis://redis:6379/1'


@pytest.mark.django_db
class TestPurgeAuditLogs:
    def _make(self, days_old):
        row = SecurityAuditLog.objects.create(action=SecurityAuditLog.ACTION_ADMIN_ACCESS)
        SecurityAuditLog.objects.filter(pk=row.pk).update(
            timestamp=timezone.now() - timedelta(days=days_old))
        return row

    def test_deletes_only_rows_past_retention(self):
        old = [self._make(400), self._make(500), self._make(366)]
        keep = [self._make(10), self._make(364)]
        out = StringIO()
        call_command('purge_audit_logs', '--days', '365', '--batch-size', '2', stdout=out)
        assert 'Deleted 3' in out.getvalue()
        assert set(SecurityAuditLog.objects.values_list('pk', flat=True)) == {r.pk for r in keep}
        assert not SecurityAuditLog.objects.filter(pk__in=[r.pk for r in old]).exists()

    def test_dry_run_deletes_nothing(self):
        self._make(400)
        out = StringIO()
        call_command('purge_audit_logs', '--days', '365', '--dry-run', stdout=out)
        assert '1 row' in out.getvalue()
        assert SecurityAuditLog.objects.count() == 1

    def test_zero_days_disables(self):
        self._make(4000)
        call_command('purge_audit_logs', '--days', '0', stdout=StringIO())
        assert SecurityAuditLog.objects.count() == 1

    def test_uses_setting_by_default(self, settings):
        settings.AUDIT_LOG_RETENTION_DAYS = 30
        self._make(31)
        self._make(5)
        call_command('purge_audit_logs', stdout=StringIO())
        assert SecurityAuditLog.objects.count() == 1
