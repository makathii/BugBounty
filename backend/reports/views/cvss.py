from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import is_admin_or_triager


class CvssActionsMixin:
    """CVSS v3.1 scoring endpoint for BugReportViewSet."""

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='cvss_score')
    def cvss_score(self, request, pk=None):
        """
        POST /api/reports/{id}/cvss_score/

        Calculate and persist a CVSS v3.1 base score for a report.
        Accepts the 8 base metric fields and returns the score + severity label.
        Saves the result back to the report (Triager/Admin only for saving).

        Request body:
        {
            "attack_vector": "N",        # N|A|L|P
            "attack_complexity": "L",    # L|H
            "privileges_required": "N",  # N|L|H
            "user_interaction": "N",     # N|R
            "scope": "U",               # U|C
            "confidentiality": "H",      # N|L|H
            "integrity": "H",            # N|L|H
            "availability": "H",         # N|L|H
            "save": true                 # optional — persist to report
        }
        """
        from core.cvss import CVSSMetrics, CVSSv3Calculator

        fields = {
            'attack_vector':       request.data.get('attack_vector', '').upper(),
            'attack_complexity':   request.data.get('attack_complexity', '').upper(),
            'privileges_required': request.data.get('privileges_required', '').upper(),
            'user_interaction':    request.data.get('user_interaction', '').upper(),
            'scope':               request.data.get('scope', '').upper(),
            'confidentiality':     request.data.get('confidentiality', '').upper(),
            'integrity':           request.data.get('integrity', '').upper(),
            'availability':        request.data.get('availability', '').upper(),
        }

        missing = [k for k, v in fields.items() if not v]
        if missing:
            return Response(
                {'detail': f"Missing required fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            metrics = CVSSMetrics(**fields)
            result = CVSSv3Calculator(metrics).calculate()
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Persist to the report if requested and user is privileged
        should_save = str(request.data.get('save', 'false')).lower() in ('true', '1', 'yes')
        if should_save:
            if not is_admin_or_triager(request):
                return Response(
                    {'detail': 'Only Triagers and Admins can save CVSS scores to reports.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            report = self.get_object()
            report.cvss_vector = result.vector_string
            report.cvss_score = result.base_score
            report.cvss_severity = result.severity
            # Auto-update Django severity to match CVSS if meaningful
            cvss_to_django = {
                'Critical': 'critical',
                'High': 'high',
                'Medium': 'medium',
                'Low': 'low',
                'None': 'low',
            }
            report.severity = cvss_to_django.get(result.severity, report.severity)
            report.save(update_fields=['cvss_vector', 'cvss_score', 'cvss_severity', 'severity'])

        return Response({
            'base_score':    result.base_score,
            'severity':      result.severity,
            'vector_string': result.vector_string,
            'iss':           result.iss,
            'ess':           result.ess,
        })
