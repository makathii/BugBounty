from django.db.models import Avg, Count, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.models import BugReport

from ..models import Company, Program
from ..permissions import _can_manage
from ..serializers import ProgramListSerializer, ProgramReportSerializer


class ProgramDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            program = get_object_or_404(Program, pk=pk)
            if not _can_manage(request.user, program):
                return Response(
                    {"error": "You don't have access to this program's dashboard."},
                    status=status.HTTP_403_FORBIDDEN
                )
            return self._program_dashboard(program, request)  

        if not request.user.groups.filter(name='ProgramOwner').exists():
            return Response(
                {"error": "Only company users can access this dashboard."},
                status=status.HTTP_403_FORBIDDEN
            )
        return self._company_dashboard(request.user, request)

    def _program_dashboard(self, program, request):
        reports = BugReport.objects.filter(program=program)
        return Response({
            'program': ProgramListSerializer(program, context={'request': request}).data,
            'total_reports': reports.count(),
            'reports_by_status': dict(
                reports.values_list('status').annotate(count=Count('id'))
            ),
            'reports_by_severity': dict(
                reports.values_list('severity').annotate(count=Count('id'))
            ),
            'total_bounties': reports.aggregate(total=Sum('bounty_amount'))['total'] or 0,
            'avg_bounty': reports.aggregate(avg=Avg('bounty_amount'))['avg'] or 0,
            'active_researchers': reports.values('reporter').distinct().count(),
            'recent_reports': ProgramReportSerializer(
                reports.select_related('reporter').order_by('-created_at')[:10],
                many=True
            ).data,
        })

    def _company_dashboard(self, user, request):
        # Check if user has completed company profile
        try:
            company_profile = Company.objects.get(user=user)
            profile_complete = True
        except Company.DoesNotExist:
            company_profile = None
            profile_complete = False

        programs = Program.objects.filter(company=user)
        all_reports = BugReport.objects.filter(program__in=programs)

        response_data = {
            'total_programs': programs.count(),
            'active_programs': programs.filter(status='active').count(),
            'total_reports': all_reports.count(),
            'total_bounties': all_reports.aggregate(total=Sum('bounty_amount'))['total'] or 0,
            'programs': ProgramListSerializer(
                programs, many=True, context={'request': request}
            ).data,
            'recent_activity': list(
                all_reports.order_by('-created_at')[:20]
                .values('id', 'title', 'program__name', 'status', 'severity', 'created_at')
            ),
            'profile_completion_required': not profile_complete,
            'profile_complete': profile_complete,
        }

        if not profile_complete:
            response_data['message'] = "Please complete your company profile to continue."
            response_data['redirect'] = "/company-registration"
        else:
            response_data['redirect'] = None
            response_data['message'] = "Welcome to your company dashboard."

        return Response(response_data)
