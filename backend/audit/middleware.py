"""
Audit logging middleware for BugBounty platform.
"""
from django.conf import settings as django_settings
from ipware import get_client_ip
from .models import SecurityAuditLog


class AuditLogMiddleware:
    """
    Middleware to automatically log security-relevant requests.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request info for logging
        request.audit_info = {
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        }

        response = self.get_response(request)

        # Log specific actions based on path and method
        self._log_request(request, response)

        return response

    def _get_client_ip(self, request):
        """
        Extract the real client IP using django-ipware.

        ipware walks the X-Forwarded-For chain from right to left, skipping
        exactly IPWARE_TRUSTED_PROXY_COUNT trusted proxy IPs (configured in
        settings). This prevents spoofing — an attacker prepending a fake IP
        to X-Forwarded-For won't land on that IP when proxies=N is set correctly.

        Set IPWARE_TRUSTED_PROXY_COUNT in settings to the number of reverse
        proxies in front of Django (e.g. 1 for a single nginx, 2 for nginx+LB).
        """
        proxy_count = getattr(django_settings, 'IPWARE_TRUSTED_PROXY_COUNT', 0)
        ip, routable = get_client_ip(request, proxy_count=proxy_count)
        if ip is None:
            # Fall back to REMOTE_ADDR if ipware can't determine the IP
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip

    def _log_request(self, request, response):
        """Log the request based on path and method"""
        path = request.path
        user = getattr(request, 'user', None)
        if user and not user.is_authenticated:
            user = None

        # Skip logging for static/media files
        if path.startswith(('/static/', '/media/', '/health')):
            return

        # Log failed authentication attempts
        if response.status_code == 403:
            SecurityAuditLog.log_permission_denied(
                user=user,
                ip_address=request.audit_info.get('ip_address'),
                user_agent=request.audit_info.get('user_agent'),
                resource=path
            )

        # Log admin access
        if path.startswith('/admin/') and user and user.is_staff:
            SecurityAuditLog.log_event(
                action=SecurityAuditLog.ACTION_ADMIN_ACCESS,
                user=user,
                ip_address=request.audit_info.get('ip_address'),
                user_agent=request.audit_info.get('user_agent'),
                success=True,
                resource_type='admin',
                resource_id=path
            )
