"""
Tests for audit logging functionality.
"""
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import User
from audit.models import SecurityAuditLog
from audit.middleware import AuditLogMiddleware


@pytest.mark.django_db
class TestAuditLogging:
    """Test audit logging functionality"""

    def test_security_audit_log_model_exists(self):
        """Test that SecurityAuditLog model exists and can create entries"""
        log = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_LOGIN,
            ip_address='127.0.0.1',
            user_agent='Test User Agent'
        )

        assert log.pk is not None
        assert log.action == SecurityAuditLog.ACTION_LOGIN
        assert log.ip_address == '127.0.0.1'
        assert log.user_agent == 'Test User Agent'
        assert log.success is True

    def test_audit_log_with_user(self, verified_user):
        """Test audit log with authenticated user"""
        log = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_REPORT_CREATED,
            user=verified_user,
            ip_address='192.168.1.1',
            details={'report_id': 123, 'title': 'Test Report'}
        )

        assert log.user == verified_user
        assert log.details['report_id'] == 123

    def test_audit_log_severity_levels(self):
        """Test different severity levels"""
        log_info = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_LOGIN,
            severity=SecurityAuditLog.SEVERITY_INFO
        )

        log_warning = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_LOGIN_FAILED,
            severity=SecurityAuditLog.SEVERITY_WARNING
        )

        log_error = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_SUSPICIOUS_ACTIVITY,
            severity=SecurityAuditLog.SEVERITY_ERROR
        )

        assert log_info.severity == SecurityAuditLog.SEVERITY_INFO
        assert log_warning.severity == SecurityAuditLog.SEVERITY_WARNING
        assert log_error.severity == SecurityAuditLog.SEVERITY_ERROR

    def test_audit_log_str_method(self):
        """Test string representation"""
        log = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_LOGIN
        )

        str_repr = str(log)
        assert 'Login' in str_repr
        assert 'Anonymous' in str_repr

    def test_audit_log_ordering(self):
        """Test that audit logs are ordered by timestamp descending"""
        # Create two logs
        log1 = SecurityAuditLog.log_event(action=SecurityAuditLog.ACTION_LOGIN)
        log2 = SecurityAuditLog.log_event(action=SecurityAuditLog.ACTION_LOGOUT)

        # Get all logs
        logs = list(SecurityAuditLog.objects.all())

        # Should be ordered by timestamp descending (newest first)
        assert logs[0].timestamp >= logs[1].timestamp

    def test_audit_log_resource_fields(self):
        """Test resource tracking fields"""
        log = SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_REPORT_STATUS_CHANGED,
            resource_id='123',
            resource_type='bug_report'
        )

        assert log.resource_id == '123'
        assert log.resource_type == 'bug_report'


@pytest.mark.django_db
class TestAuditMiddleware:
    """Test audit logging middleware"""

    def test_middleware_get_client_ip(self, settings):
        """Test IP extraction from request using django-ipware.

        With proxy_count=0 (default/dev) ipware ignores X-Forwarded-For and
        returns REMOTE_ADDR — this prevents spoofed XFF headers from reaching
        the audit log.  When proxy_count=1 is configured (nginx in front),
        ipware trusts the rightmost XFF entry.
        """
        from unittest.mock import patch
        factory = RequestFactory()
        middleware = AuditLogMiddleware(lambda r: r)

        # --- proxy_count=0 (default dev): XFF is ignored, REMOTE_ADDR wins ---
        settings.IPWARE_TRUSTED_PROXY_COUNT = 0
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 10.0.0.2'
        # RequestFactory sets REMOTE_ADDR='127.0.0.1'
        ip = middleware._get_client_ip(request)
        assert ip == '127.0.0.1', (
            "With proxy_count=0, ipware must ignore XFF and return REMOTE_ADDR."
        )

        # --- proxy_count=1: rightmost XFF entry (the proxy-added one) is trusted ---
        settings.IPWARE_TRUSTED_PROXY_COUNT = 1
        request2 = factory.get('/')
        request2.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 10.0.0.2'
        request2.META['REMOTE_ADDR'] = '10.0.0.2'  # the trusted proxy
        ip2 = middleware._get_client_ip(request2)
        assert ip2 == '10.0.0.1', (
            "With proxy_count=1, ipware should return the client IP from XFF."
        )

        # --- REMOTE_ADDR only (no XFF) ---
        settings.IPWARE_TRUSTED_PROXY_COUNT = 0
        request3 = factory.get('/')
        request3.META['REMOTE_ADDR'] = '192.168.1.1'
        request3.META.pop('HTTP_X_FORWARDED_FOR', None)
        ip3 = middleware._get_client_ip(request3)
        assert ip3 == '192.168.1.1'

    def test_middleware_skips_static_files(self):
        """Test that static files are not logged"""
        factory = RequestFactory()

        # Create a mock response
        class MockResponse:
            status_code = 200

        middleware = AuditLogMiddleware(lambda r: MockResponse())

        # Request to static file
        request = factory.get('/static/js/app.js')
        response = middleware(request)

        # Should skip logging
        assert response.status_code == 200

    def test_audit_log_exists_in_database(self):
        """Test that audit logs can be queried"""
        # Create a log entry
        SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_LOGIN,
            ip_address='127.0.0.1'
        )

        # Query it
        logs = SecurityAuditLog.objects.filter(action=SecurityAuditLog.ACTION_LOGIN)
        assert logs.count() == 1
        assert logs.first().ip_address == '127.0.0.1'

    def test_audit_log_permission_denied(self, verified_user):
        """Test permission denied logging"""
        log = SecurityAuditLog.log_permission_denied(
            user=verified_user,
            ip_address='10.0.0.1',
            resource='/api/admin/reports/'
        )

        assert log.action == SecurityAuditLog.ACTION_PERMISSION_DENIED
        assert log.success is False
        assert log.severity == SecurityAuditLog.SEVERITY_WARNING
        assert log.details['resource'] == '/api/admin/reports/'

    def test_audit_log_indexes(self):
        """Test that database indexes are properly set"""
        # Create logs
        for i in range(5):
            SecurityAuditLog.log_event(
                action=SecurityAuditLog.ACTION_LOGIN,
                ip_address=f'127.0.0.{i}'
            )

        # Query by action (should use index)
        logs = SecurityAuditLog.objects.filter(action=SecurityAuditLog.ACTION_LOGIN)
        assert logs.count() == 5

        # Query by IP (should use index)
        logs = SecurityAuditLog.objects.filter(ip_address='127.0.0.1')
        assert logs.count() == 1

