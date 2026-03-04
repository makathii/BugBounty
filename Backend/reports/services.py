from .models import ActivityLog


class ActivityLogger:
    @staticmethod
    def log_status_change(report, user, old_status, new_status):
        ActivityLog.objects.create(
            report=report,
            user=user,
            action='status_change',
            details={
                'old_status': old_status,
                'new_status': new_status,
                'message': f"Status changed from {old_status} to {new_status}"
            }
        )

    @staticmethod
    def log_verification(report, user, action, reason=""):
        ActivityLog.objects.create(
            report=report,
            user=user,
            action=action,  # 'accept' or 'reject'
            details={
                'reason': reason,
                'message': f"Report {action}ed by {user.username}"
            }
        )

    @staticmethod
    def log_comment(report, user):
        ActivityLog.objects.create(
            report=report,
            user=user,
            action='comment',
            details={
                'message': f"Comment added by {user.username}"
            }
        )

    @staticmethod
    def log_assignment(report, user, assigned_to):
        ActivityLog.objects.create(
            report=report,
            user=user,
            action='assignment',
            details={
                'assigned_to': assigned_to.username,
                'message': f"Report assigned to {assigned_to.username}"
            }
        )