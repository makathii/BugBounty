"""
Audit logging models for the BugBounty platform.
"""
from django.db import models
from django.contrib.auth.models import User


class SecurityAuditLog(models.Model):
    """
    Comprehensive security audit log for tracking user actions.
    """
    # Action types
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_REGISTER = 'register'
    ACTION_PASSWORD_CHANGE = 'password_change'
    ACTION_PASSWORD_RESET_REQUEST = 'password_reset_request'
    ACTION_PASSWORD_RESET_COMPLETE = 'password_reset_complete'
    ACTION_EMAIL_VERIFIED = 'email_verified'
    ACTION_REPORT_CREATED = 'report_created'
    ACTION_REPORT_UPDATED = 'report_updated'
    ACTION_REPORT_STATUS_CHANGED = 'report_status_changed'
    ACTION_REPORT_MARKED_DUPLICATE = 'report_marked_duplicate'
    ACTION_ATTACHMENT_UPLOADED = 'attachment_uploaded'
    ACTION_ATTACHMENT_DOWNLOADED = 'attachment_downloaded'
    ACTION_PROGRAM_CREATED = 'program_created'
    ACTION_PROGRAM_UPDATED = 'program_updated'
    ACTION_COMPANY_PROFILE_CREATED = 'company_profile_created'
    ACTION_SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    ACTION_PERMISSION_DENIED = 'permission_denied'
    ACTION_ADMIN_ACCESS = 'admin_access'

    ACTION_CHOICES = [
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_LOGIN_FAILED, 'Login Failed'),
        (ACTION_REGISTER, 'Register'),
        (ACTION_PASSWORD_CHANGE, 'Password Change'),
        (ACTION_PASSWORD_RESET_REQUEST, 'Password Reset Request'),
        (ACTION_PASSWORD_RESET_COMPLETE, 'Password Reset Complete'),
        (ACTION_EMAIL_VERIFIED, 'Email Verified'),
        (ACTION_REPORT_CREATED, 'Report Created'),
        (ACTION_REPORT_UPDATED, 'Report Updated'),
        (ACTION_REPORT_STATUS_CHANGED, 'Report Status Changed'),
        (ACTION_REPORT_MARKED_DUPLICATE, 'Report Marked Duplicate'),
        (ACTION_ATTACHMENT_UPLOADED, 'Attachment Uploaded'),
        (ACTION_ATTACHMENT_DOWNLOADED, 'Attachment Downloaded'),
        (ACTION_PROGRAM_CREATED, 'Program Created'),
        (ACTION_PROGRAM_UPDATED, 'Program Updated'),
        (ACTION_COMPANY_PROFILE_CREATED, 'Company Profile Created'),
        (ACTION_SUSPICIOUS_ACTIVITY, 'Suspicious Activity'),
        (ACTION_PERMISSION_DENIED, 'Permission Denied'),
        (ACTION_ADMIN_ACCESS, 'Admin Access'),
    ]

    # Severity levels
    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_ERROR = 'error'
    SEVERITY_CRITICAL = 'critical'

    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_ERROR, 'Error'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='security_audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    details = models.JSONField(default=dict, blank=True)
    resource_id = models.CharField(max_length=100, blank=True, help_text="ID of affected resource")
    resource_type = models.CharField(max_length=50, blank=True, help_text="Type of affected resource")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Security Audit Log'
        verbose_name_plural = 'Security Audit Logs'
        indexes = [
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.get_action_display()} - {self.user or 'Anonymous'}"

    @classmethod
    def log_event(cls, action, user=None, ip_address=None, user_agent='',
                  success=True, details=None, severity=SEVERITY_INFO,
                  resource_id='', resource_type=''):
        """
        Log a security event.
        """
        return cls.objects.create(
            action=action,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent[:512] if user_agent else '',  # Truncate long user agents
            success=success,
            details=details or {},
            severity=severity,
            resource_id=str(resource_id) if resource_id else '',
            resource_type=resource_type
        )

    @classmethod
    def log_login_attempt(cls, user, ip_address, success, user_agent='', details=None):
        """Log a login attempt"""
        action = cls.ACTION_LOGIN if success else cls.ACTION_LOGIN_FAILED
        severity = cls.SEVERITY_INFO if success else cls.SEVERITY_WARNING

        log_entry = cls.log_event(
            action=action,
            user=user if success else None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            severity=severity,
            details=details
        )

        # Check for suspicious activity (multiple failed logins)
        if not success:
            recent_failures = cls.objects.filter(
                action=cls.ACTION_LOGIN_FAILED,
                ip_address=ip_address,
                timestamp__gte=models.functions.Now() - models.F('timestamp')
            ).count()

            # If more than 5 failed attempts in last hour from same IP
            if recent_failures >= 5:
                cls.log_event(
                    action=cls.ACTION_SUSPICIOUS_ACTIVITY,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    severity=cls.SEVERITY_WARNING,
                    details={
                        'message': f'Multiple failed login attempts ({recent_failures})',
                        'attempted_username': details.get('username') if details else None
                    }
                )

        return log_entry

    @classmethod
    def log_permission_denied(cls, user, ip_address, user_agent='', resource=None):
        """Log permission denied events"""
        return cls.log_event(
            action=cls.ACTION_PERMISSION_DENIED,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            severity=cls.SEVERITY_WARNING,
            details={'resource': resource}
        )
