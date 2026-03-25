from django.shortcuts import get_object_or_404
from urllib3 import request
#from Backend.tests.conftest import program
from rest_framework import viewsets, generics, permissions, status, filters
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum, Avg
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Program, Scope, ProgramInvitation, ProgramApplication,
    ProgramFavorite, ProgramNotification
)
from .serializers import (
    ProgramListSerializer, ProgramDetailSerializer, ProgramCreateSerializer,
    ProgramUpdateSerializer, ScopeSerializer, ProgramInvitationSerializer,
    ProgramApplicationSerializer, ProgramFavoriteSerializer,
    ProgramNotificationSerializer, ProgramReportSerializer, PublicProgramSerializer
)
from reports.models import BugReport
from .permissions import (
    IsProgramOwnerOrAdmin, IsResearcher, CanAccessProgram,
    _is_admin, _can_manage, _researcher_has_private_access
)


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

class ProgramViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type', 'status', 'company']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['created_at', 'published_at', 'total_reports', 'total_bounties', 'avg_severity_score']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ProgramCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ProgramUpdateSerializer
        if self.action == 'retrieve':
            return ProgramDetailSerializer
        return ProgramListSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            perms = [permissions.IsAuthenticated, IsProgramOwnerOrAdmin]
        else:
            perms = [permissions.IsAuthenticated]
        return [p() for p in perms]

    def get_queryset(self):
        user = self.request.user
        qs = Program.objects.select_related('company')

        if _is_admin(user):
            return qs

        if user.groups.filter(name='ProgramOwner').exists():
            return qs.filter(company=user)

        if user.groups.filter(name='User').exists():
            public = qs.filter(scope_type__in=['public', 'vdp'], status='active')
            invited = qs.filter(
                scope_type='private', status='active',
                invitations__researcher=user, invitations__status='accepted'
            )
            applied = qs.filter(
                scope_type='private', status='active',
                applications__researcher=user, applications__status='approved'
            )
            return (public | invited | applied).distinct()

        if user.groups.filter(name='Triager').exists():
            return qs.filter(status='active')

        return qs.none()

    def get_object(self):
        return get_object_or_404(
            Program.objects
            .select_related('company')
            .prefetch_related(
                'scopes',
                'invitations__researcher',
                'applications__researcher',
                'favorites',
            ),
            pk=self.kwargs['pk']
        )

    def perform_create(self, serializer):
        serializer.save(company=self.request.user)

    # --- Status transitions ---

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        program = self.get_object()
        if not _can_manage(request.user, program):
            return Response(
                {"error": "You don't have permission to activate this program."},
                status=status.HTTP_403_FORBIDDEN
            )
        if not program.scopes.filter(is_in_scope=True).exists():
            return Response(
                {"error": "Program must have at least one in-scope target before activation."},
                status=status.HTTP_400_BAD_REQUEST
            )
        program.status = 'active'
        program.save()
        return Response({
            "message": "Program activated successfully.",
            "status": program.status,
            "published_at": program.published_at,
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        program = self.get_object()
        if not _can_manage(request.user, program):
            return Response(
                {"error": "You don't have permission to pause this program."},
                status=status.HTTP_403_FORBIDDEN
            )
        program.status = 'paused'
        program.save()
        return Response({"message": "Program paused.", "status": program.status})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        program = self.get_object()
        if not _can_manage(request.user, program):
            return Response(
                {"error": "You don't have permission to close this program."},
                status=status.HTTP_403_FORBIDDEN
            )
        program.status = 'closed'
        program.save()
        return Response({"message": "Program closed.", "status": program.status})

    # --- Join ---

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        program = self.get_object()
        user = request.user

        if not user.groups.filter(name='Researcher').exists():
            return Response(
                {"error": "Only researchers can join programs."},
                status=status.HTTP_403_FORBIDDEN
            )
        if program.status != 'active':
            return Response(
                {"error": "This program is not currently active."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if CanAccessProgram().has_object_permission(request, self, program):
            return Response(
                {"error": "You already have access to this program."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if program.scope_type in ('public', 'vdp'):
            return Response(
                {"message": "You can submit reports to this program directly."},
                status=status.HTTP_200_OK
            )

        if program.invitation_only:
            invitation = ProgramInvitation.objects.filter(
                program=program, researcher=user, status='pending'
            ).first()
            if not invitation:
                return Response(
                    {"error": "This program is invitation-only. You need a pending invitation to join."},
                    status=status.HTTP_403_FORBIDDEN
                )
            try:
                invitation.accept()
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"message": "Invitation accepted. You now have access to this program."},
                status=status.HTTP_200_OK
            )

        if program.requires_application:
            existing = ProgramApplication.objects.filter(
                program=program, researcher=user
            ).first()
            if existing:
                return Response(
                    {"error": f"You already have a {existing.status} application for this program."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ProgramApplication.objects.create(
                program=program,
                researcher=user,
                message=request.data.get('message', ''),
                experience=request.data.get('experience', ''),
                qualifications=request.data.get('qualifications', ''),
            )
            return Response(
                {"message": "Application submitted. You will be notified once it's reviewed."},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"error": "You do not have access to this program."},
            status=status.HTTP_403_FORBIDDEN
        )

    # --- Data endpoints ---

    @action(detail=True, methods=['get'])
    def reports(self, request, pk=None):
        program = self.get_object()
        if not CanAccessProgram().has_object_permission(request, self, program):
            return Response(
                {"error": "You don't have access to this program."},
                status=status.HTTP_403_FORBIDDEN
            )
        reports = BugReport.objects.filter(program=program).select_related(
            'reporter'
        ).order_by('-created_at')
        return Response(ProgramReportSerializer(reports, many=True).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        program = self.get_object()
        can_view = (
            _can_manage(request.user, program) or
            request.user.groups.filter(name='Triager').exists() or
            CanAccessProgram().has_object_permission(request, self, program)
        )
        if not can_view:
            return Response(
                {"error": "You don't have access to program statistics."},
                status=status.HTTP_403_FORBIDDEN
            )
        reports = BugReport.objects.filter(program=program)
        return Response({
            'total_reports': reports.count(),
            'reports_by_status': dict(
                reports.values_list('status').annotate(count=Count('id'))
            ),
            'reports_by_severity': dict(
                reports.values_list('severity').annotate(count=Count('id'))
            ),
            'total_bounties': reports.aggregate(total=Sum('bounty_amount'))['total'] or 0,
            'avg_bounty': reports.aggregate(avg=Avg('bounty_amount'))['avg'] or 0,
            'top_researchers': list(
                reports.values('reporter__username')
                .annotate(report_count=Count('id'), total_bounty=Sum('bounty_amount'))
                .order_by('-total_bounty')[:10]
            ),
            'recent_activity': list(
                reports.order_by('-created_at')[:10]
                .values('id', 'title', 'status', 'severity', 'created_at')
            ),
        })


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

class ScopeViewSet(viewsets.ModelViewSet):
    serializer_class = ScopeSerializer
    permission_classes = [permissions.IsAuthenticated, IsProgramOwnerOrAdmin]

    def get_queryset(self):
        return Scope.objects.filter(
            program_id=self.kwargs['program_pk']
        ).select_related('program')

    def perform_create(self, serializer):
        program = get_object_or_404(Program, pk=self.kwargs['program_pk'])
        serializer.save(program=program)


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

class ProgramInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        program_id = self.kwargs.get('program_pk')
        qs = ProgramInvitation.objects.select_related('program', 'researcher', 'invited_by')

        if program_id:
            program = get_object_or_404(Program, pk=program_id)
            if _can_manage(user, program):
                return qs.filter(program_id=program_id)
            return qs.filter(program_id=program_id, researcher=user)

        return qs.filter(researcher=user)

    def perform_create(self, serializer):
        program = get_object_or_404(Program, pk=self.kwargs['program_pk'])
        if program.scope_type != 'private':
            raise drf_serializers.ValidationError(
                {"program": "Invitations are only allowed for private programs."}
            )
        if not _can_manage(self.request.user, program):
            raise drf_serializers.ValidationError(
                {"program": "Only the program owner or an admin can send invitations."}
            )
        serializer.save(program=program, invited_by=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None, program_pk=None):
        invitation = self.get_object()
        if invitation.researcher != request.user:
            return Response(
                {"error": "You can only accept your own invitations."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            invitation.accept()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Invitation accepted.", "status": invitation.status})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None, program_pk=None):
        invitation = self.get_object()
        if invitation.researcher != request.user:
            return Response(
                {"error": "You can only reject your own invitations."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            invitation.reject()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Invitation rejected.", "status": invitation.status})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None, program_pk=None):
        invitation = self.get_object()
        program = get_object_or_404(Program, pk=program_pk)
        if not _can_manage(request.user, program):
            return Response(
                {"error": "Only the program owner or an admin can revoke invitations."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            invitation.revoke()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Invitation revoked.", "status": invitation.status})


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

class ProgramApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        program_id = self.kwargs.get('program_pk')
        qs = ProgramApplication.objects.select_related('program', 'researcher', 'reviewed_by')

        if program_id:
            program = get_object_or_404(Program, pk=program_id)
            if _can_manage(user, program):
                return qs.filter(program_id=program_id)
            return qs.filter(program_id=program_id, researcher=user)

        return qs.filter(researcher=user)

    def perform_create(self, serializer):
        program = get_object_or_404(Program, pk=self.kwargs['program_pk'])
        if not program.requires_application:
            raise drf_serializers.ValidationError(
                {"program": "This program does not accept applications."}
            )
        if ProgramApplication.objects.filter(program=program, researcher=self.request.user).exists():
            raise drf_serializers.ValidationError(
                {"program": "You have already applied to this program."}
            )
        serializer.save(program=program, researcher=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None, program_pk=None):
        application = self.get_object()
        if not _can_manage(request.user, application.program):
            return Response(
                {"error": "You don't have permission to approve applications."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            application.approve(
                reviewed_by=request.user,
                notes=request.data.get('review_notes', '')
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Application approved.", "status": application.status})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None, program_pk=None):
        application = self.get_object()
        if not _can_manage(request.user, application.program):
            return Response(
                {"error": "You don't have permission to reject applications."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            application.reject(
                reviewed_by=request.user,
                notes=request.data.get('review_notes', '')
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Application rejected.", "status": application.status})

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None, program_pk=None):
        application = self.get_object()
        if application.researcher != request.user:
            return Response(
                {"error": "You can only withdraw your own application."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            application.withdraw()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Application withdrawn.", "status": application.status})


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------

class ProgramFavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated, IsResearcher]

    def get_queryset(self):
        return ProgramFavorite.objects.filter(
            researcher=self.request.user
        ).select_related('program')

    def perform_create(self, serializer):
        program = serializer.validated_data['program']
        if not CanAccessProgram().has_object_permission(self.request, self, program):
            raise drf_serializers.ValidationError(
                {"program": "You don't have access to this program."}
            )
        serializer.save(researcher=self.request.user)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class ProgramNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProgramNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProgramNotification.objects.filter(
            user=self.request.user
        ).select_related('program')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response({"message": "Marked as read."})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = ProgramNotification.objects.filter(
            user=request.user, read=False
        ).update(read=True)
        return Response({"message": f"{updated} notification(s) marked as read."})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = ProgramNotification.objects.filter(
            user=request.user, read=False
        ).count()
        return Response({"unread_count": count})


# ---------------------------------------------------------------------------
# Program list views
# ---------------------------------------------------------------------------

class ResearcherProgramListView(generics.ListAPIView):
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated, IsResearcher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['created_at', 'published_at', 'total_reports', 'total_bounties']
    ordering = ['-published_at']

    def get_queryset(self):
        user = self.request.user
        public = Program.objects.filter(scope_type__in=['public', 'vdp'], status='active')
        invited = Program.objects.filter(
            scope_type='private', status='active',
            invitations__researcher=user, invitations__status='accepted'
        )
        applied = Program.objects.filter(
            scope_type='private', status='active',
            applications__researcher=user, applications__status='approved'
        )
        return (public | invited | applied).distinct().select_related('company')


class CompanyProgramListView(generics.ListAPIView):
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.groups.filter(name='Company').exists():
            return Program.objects.none()
        return Program.objects.filter(
            company=self.request.user
        ).select_related('company')


class PublicProgramListView(generics.ListAPIView):
    serializer_class = PublicProgramSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['published_at', 'total_reports', 'total_bounties']
    ordering = ['-published_at']

    def get_queryset(self):
        return Program.objects.filter(
            scope_type__in=['public', 'vdp'], status='active'
        ).select_related('company')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

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

        if not request.user.groups.filter(name='Company').exists():
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
        programs = Program.objects.filter(company=user)
        all_reports = BugReport.objects.filter(program__in=programs)
        return Response({
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
     })



# ---------------------------------------------------------------------------
# API root
# ---------------------------------------------------------------------------

@api_view(['GET'])
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
        'favorites': '/api/favorites/',
        'notifications': '/api/notifications/',
        'join_program': '/api/programs/{id}/join/',
    })