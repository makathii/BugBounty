"""
Audit logging middleware for BugBounty platform.
"""
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
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
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
