from rest_framework import viewsets, generics, permissions, status, filters
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Sum, Avg, F
from django.contrib.auth.models import User
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models import Program, Scope, ProgramInvitation, ProgramApplication, ProgramStats, ProgramFavorite, \
    ProgramNotification
from .serializers import (
    ProgramListSerializer, ProgramDetailSerializer, ProgramCreateSerializer,
    ProgramUpdateSerializer, ScopeSerializer, ProgramInvitationSerializer,
    ProgramApplicationSerializer, ProgramStatsSerializer, ProgramFavoriteSerializer,
    ProgramNotificationSerializer, ProgramReportSerializer, PublicProgramSerializer
)
from reports.models import BugReport
from .permissions import IsProgramOwnerOrAdmin, IsResearcher, CanAccessProgram


class ProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for Program model"""
    queryset = Program.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type', 'status', 'company']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['created_at', 'published_at', 'total_reports', 'total_bounties', 'avg_severity_score']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ProgramCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProgramUpdateSerializer
        elif self.action == 'retrieve':
            return ProgramDetailSerializer
        return ProgramListSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsProgramOwnerOrAdmin]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Admins can see everything
        if user.is_superuser or user.groups.filter(name='Admin').exists():
            return queryset

        # Company users see their own programs
        if user.groups.filter(name='Company').exists():
            return queryset.filter(company=user)

        # Researchers see public programs and ones they have access to
        if user.groups.filter(name='Researcher').exists():
            # Get public programs
            public_programs = queryset.filter(
                scope_type='public',
                status='active'
            )

            # Get private programs where researcher is invited/accepted
            invited_programs = queryset.filter(
                scope_type='private',
                status='active',
                invitations__researcher=user,
                invitations__status='accepted'
            )

            # Get private programs where researcher application was approved
            applied_programs = queryset.filter(
                scope_type='private',
                status='active',
                applications__researcher=user,
                applications__status='approved'
            )

            # Combine all querysets
            return (public_programs | invited_programs | applied_programs).distinct()

        # Triagers can see all active programs
        if user.groups.filter(name='Triager').exists():
            return queryset.filter(status='active')

        return queryset.none()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a program (change status from draft to active)"""
        program = self.get_object()

        # Check permissions
        if not (program.company == request.user or request.user.groups.filter(name='Admin').exists()):
            return Response(
                {"error": "You don't have permission to activate this program"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Ensure program has at least one in-scope target
        if program.scopes.filter(is_in_scope=True).count() == 0:
            return Response(
                {"error": "Program must have at least one in-scope target before activation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        program.status = 'active'
        program.save()

        return Response({
            "message": "Program activated successfully",
            "status": program.status,
            "published_at": program.published_at
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a program"""
        program = self.get_object()

        # Check permissions
        if not (program.company == request.user or request.user.groups.filter(name='Admin').exists()):
            return Response(
                {"error": "You don't have permission to pause this program"},
                status=status.HTTP_403_FORBIDDEN
            )

        program.status = 'paused'
        program.save()

        return Response({
            "message": "Program paused successfully",
            "status": program.status
        })

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a program"""
        program = self.get_object()

        # Check permissions
        if not (program.company == request.user or request.user.groups.filter(name='Admin').exists()):
            return Response(
                {"error": "You don't have permission to close this program"},
                status=status.HTTP_403_FORBIDDEN
            )

        program.status = 'closed'
        program.save()

        return Response({
            "message": "Program closed successfully",
            "status": program.status
        })

    @action(detail=True, methods=['get'])
    def reports(self, request, pk=None):
        """Get reports for this program"""
        program = self.get_object()

        # Check if user can access this program
        if not CanAccessProgram().has_object_permission(request, self, program):
            return Response(
                {"error": "You don't have access to this program"},
                status=status.HTTP_403_FORBIDDEN
            )

        reports = BugReport.objects.filter(program=program).order_by('-created_at')
        serializer = ProgramReportSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get detailed statistics for this program"""
        program = self.get_object()

        # Check if user can access this program
        if not (program.company == request.user or
                request.user.groups.filter(name__in=['Admin', 'Triager']).exists() or
                CanAccessProgram().has_object_permission(request, self, program)):
            return Response(
                {"error": "You don't have access to program statistics"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Calculate stats
        reports = BugReport.objects.filter(program=program)

        stats = {
            'total_reports': reports.count(),
            'reports_by_status': dict(reports.values_list('status').annotate(count=Count('id'))),
            'reports_by_severity': dict(reports.values_list('severity').annotate(count=Count('id'))),
            'total_bounties': reports.aggregate(total=Sum('bounty_amount'))['total'] or 0,
            'avg_bounty': reports.aggregate(avg=Avg('bounty_amount'))['avg'] or 0,
            'top_researchers': list(
                reports.values('reporter__username')
                .annotate(
                    report_count=Count('id'),
                    total_bounty=Sum('bounty_amount')
                )
                .order_by('-total_bounty')[:10]
            ),
            'recent_activity': reports.order_by('-created_at')[:10].values(
                'id', 'title', 'status', 'severity', 'created_at'
            )
        }

        return Response(stats)


class ScopeViewSet(viewsets.ModelViewSet):
    """ViewSet for Scope model"""
    serializer_class = ScopeSerializer
    permission_classes = [permissions.IsAuthenticated, IsProgramOwnerOrAdmin]

    def get_queryset(self):
        program_id = self.kwargs.get('program_pk')
        return Scope.objects.filter(program_id=program_id)

    def perform_create(self, serializer):
        program_id = self.kwargs.get('program_pk')
        program = Program.objects.get(id=program_id)
        serializer.save(program=program)


class ProgramInvitationViewSet(viewsets.ModelViewSet):
    """ViewSet for ProgramInvitation model"""
    serializer_class = ProgramInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        program_id = self.kwargs.get('program_pk')

        if program_id:
            # For program-specific invitations
            program = Program.objects.get(id=program_id)

            # Program owner or admin can see all invitations
            if program.company == user or user.groups.filter(name='Admin').exists():
                return ProgramInvitation.objects.filter(program_id=program_id)

            # Researchers can only see their own invitations
            return ProgramInvitation.objects.filter(program_id=program_id, researcher=user)
        else:
            # For user's invitations
            return ProgramInvitation.objects.filter(researcher=user)

    def perform_create(self, serializer):
        program_id = self.kwargs.get('program_pk')
        program = Program.objects.get(id=program_id)

        # Check if program is private
        if program.scope_type != 'private':
            raise serializers.ValidationError(
                "Invitations are only allowed for private programs"
            )

        serializer.save(
            program=program,
            invited_by=self.request.user
        )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None, program_pk=None):
        """Accept an invitation"""
        invitation = self.get_object()

        if invitation.researcher != request.user:
            return Response(
                {"error": "You can only accept your own invitations"},
                status=status.HTTP_403_FORBIDDEN
            )

        if invitation.status != 'pending':
            return Response(
                {"error": f"Invitation is already {invitation.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation.status = 'accepted'
        invitation.save()

        return Response({
            "message": "Invitation accepted successfully",
            "status": invitation.status
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None, program_pk=None):
        """Reject an invitation"""
        invitation = self.get_object()

        if invitation.researcher != request.user:
            return Response(
                {"error": "You can only reject your own invitations"},
                status=status.HTTP_403_FORBIDDEN
            )

        if invitation.status != 'pending':
            return Response(
                {"error": f"Invitation is already {invitation.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation.status = 'rejected'
        invitation.save()

        return Response({
            "message": "Invitation rejected",
            "status": invitation.status
        })


class ProgramApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for ProgramApplication model"""
    serializer_class = ProgramApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        program_id = self.kwargs.get('program_pk')

        if program_id:
            program = Program.objects.get(id=program_id)

            # Program owner or admin can see all applications
            if program.company == user or user.groups.filter(name='Admin').exists():
                return ProgramApplication.objects.filter(program_id=program_id)

            # Researchers can only see their own applications
            return ProgramApplication.objects.filter(program_id=program_id, researcher=user)
        else:
            # For user's applications
            return ProgramApplication.objects.filter(researcher=user)

    def perform_create(self, serializer):
        program_id = self.kwargs.get('program_pk')
        program = Program.objects.get(id=program_id)

        # Check if program accepts applications
        if not program.requires_application:
            raise serializers.ValidationError(
                "This program does not accept applications"
            )

        serializer.save(
            program=program,
            researcher=self.request.user
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None, program_pk=None):
        """Approve an application (program owner/admin only)"""
        application = self.get_object()
        program = application.program

        # Check permissions
        if not (program.company == request.user or request.user.groups.filter(name='Admin').exists()):
            return Response(
                {"error": "You don't have permission to approve applications"},
                status=status.HTTP_403_FORBIDDEN
            )

        if application.status != 'pending':
            return Response(
                {"error": f"Application is already {application.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = 'approved'
        application.reviewed_by = request.user
        application.save()

        return Response({
            "message": "Application approved successfully",
            "status": application.status
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None, program_pk=None):
        """Reject an application (program owner/admin only)"""
        application = self.get_object()
        program = application.program

        # Check permissions
        if not (program.company == request.user or request.user.groups.filter(name='Admin').exists()):
            return Response(
                {"error": "You don't have permission to reject applications"},
                status=status.HTTP_403_FORBIDDEN
            )

        if application.status != 'pending':
            return Response(
                {"error": f"Application is already {application.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        application.status = 'rejected'
        application.reviewed_by = request.user
        application.save()

        return Response({
            "message": "Application rejected",
            "status": application.status
        })


class ProgramFavoriteViewSet(viewsets.ModelViewSet):
    """ViewSet for ProgramFavorite model"""
    serializer_class = ProgramFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated, IsResearcher]

    def get_queryset(self):
        return ProgramFavorite.objects.filter(researcher=self.request.user)

    def perform_create(self, serializer):
        program = serializer.validated_data['program']

        # Check if user can access this program
        if not CanAccessProgram().has_object_permission(self.request, self, program):
            raise serializers.ValidationError("You don't have access to this program")

        serializer.save(researcher=self.request.user)


class ResearcherProgramListView(generics.ListAPIView):
    """List programs available to researchers"""
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated, IsResearcher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['created_at', 'published_at', 'total_reports', 'total_bounties']
    ordering = ['-published_at']

    def get_queryset(self):
        user = self.request.user

        # Get public programs
        public_programs = Program.objects.filter(
            scope_type='public',
            status='active'
        )

        # Get private programs where researcher is invited/accepted
        invited_programs = Program.objects.filter(
            scope_type='private',
            status='active',
            invitations__researcher=user,
            invitations__status='accepted'
        )

        # Get private programs where researcher application was approved
        applied_programs = Program.objects.filter(
            scope_type='private',
            status='active',
            applications__researcher=user,
            applications__status='approved'
        )

        # Combine all querysets
        return (public_programs | invited_programs | applied_programs).distinct()


class CompanyProgramListView(generics.ListAPIView):
    """List programs for a company user"""
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only company users can see this
        if not self.request.user.groups.filter(name='Company').exists():
            return Program.objects.none()

        return Program.objects.filter(company=self.request.user)


class PublicProgramListView(generics.ListAPIView):
    """Public view of programs (no authentication required)"""
    serializer_class = PublicProgramSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['published_at', 'total_reports', 'total_bounties']
    ordering = ['-published_at']

    def get_queryset(self):
        return Program.objects.filter(
            scope_type='public',
            status='active'
        )


class ProgramDashboardView(APIView):
    """Dashboard view for program owners"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            # Single program dashboard
            try:
                program = Program.objects.get(id=pk)
            except Program.DoesNotExist:
                return Response(
                    {"error": "Program not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check permissions
            if not (program.company == request.user or request.user.groups.filter(name='Admin').exists()):
                return Response(
                    {"error": "You don't have access to this program's dashboard"},
                    status=status.HTTP_403_FORBIDDEN
                )

            return self.get_program_dashboard(program)
        else:
            # Company dashboard - all programs
            if not request.user.groups.filter(name='Company').exists():
                return Response(
                    {"error": "Only company users can access this dashboard"},
                    status=status.HTTP_403_FORBIDDEN
                )

            return self.get_company_dashboard(request.user)

    def get_program_dashboard(self, program):
        """Get dashboard data for a single program"""
        reports = BugReport.objects.filter(program=program)

        # Calculate stats
        stats = {
            'program': ProgramListSerializer(program).data,
            'total_reports': reports.count(),
            'reports_by_status': dict(reports.values_list('status').annotate(count=Count('id'))),
            'reports_by_severity': dict(reports.values_list('severity').annotate(count=Count('id'))),
            'total_bounties': reports.aggregate(total=Sum('bounty_amount'))['total'] or 0,
            'avg_bounty': reports.aggregate(avg=Avg('bounty_amount'))['avg'] or 0,
            'active_researchers': reports.values('reporter').distinct().count(),
            'recent_reports': ProgramReportSerializer(reports.order_by('-created_at')[:10], many=True).data
        }

        return Response(stats)

    def get_company_dashboard(self, user):
        """Get dashboard data for all company programs"""
        programs = Program.objects.filter(company=user)
        all_reports = BugReport.objects.filter(program__in=programs)

        # Calculate overall stats
        stats = {
            'total_programs': programs.count(),
            'active_programs': programs.filter(status='active').count(),
            'total_reports': all_reports.count(),
            'total_bounties': all_reports.aggregate(total=Sum('bounty_amount'))['total'] or 0,
            'programs': ProgramListSerializer(programs, many=True).data,
            'recent_activity': all_reports.order_by('-created_at')[:20].values(
                'id', 'title', 'program__name', 'status', 'severity', 'created_at'
            )
        }

        return Response(stats)


@permission_classes([permissions.AllowAny])
def program_api_root(request):
    return Response({
        'company_programs': '/api/programs/company/',
        'researcher_programs': '/api/programs/researcher/',
        'public_programs': '/api/programs/public/',
        'program_detail': '/api/programs/{id}/',
        'program_dashboard': '/api/programs/{id}/dashboard/',
        'program_scopes': '/api/programs/{id}/scopes/',
        'program_invitations': '/api/programs/{id}/invitations/',
        'program_applications': '/api/programs/{id}/applications/',
        'program_favorites': '/api/programs/favorites/',
    })