from django.db.models import Avg, Count, F, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.roles import has_any_role
from leaderboard.models import ScoreEvent
from reports.models import BugReport

from ..models import Program, ProgramApplication, ProgramFavorite, ProgramInvitation
from ..permissions import CanAccessProgram, IsProgramOwnerOrAdmin, _can_manage, _is_admin
from ..serializers import (
    ProgramCreateSerializer,
    ProgramDetailSerializer,
    ProgramListSerializer,
    ProgramReportSerializer,
    ProgramUpdateSerializer,
)


def with_favorites_total(qs):
    """
    Annotate ``favorites_total`` so ProgramListSerializer needn't COUNT per row.
    Correlated subquery (not a JOIN) so the count is immune to row
    multiplication from the invitation/application joins + distinct().
    """
    total = Coalesce(
        Subquery(
            ProgramFavorite.objects.filter(program=OuterRef('pk'))
            .order_by().values('program')
            .annotate(c=Count('pk')).values('c'),
            output_field=IntegerField(),
        ),
        0,
    )
    return qs.annotate(favorites_total=total)


class ProgramViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type', 'status', 'company']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['created_at', 'published_at', 'total_reports', 'total_points', 'avg_severity_score']
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
        return with_favorites_total(self._visible_programs())

    def _visible_programs(self):
        user = self.request.user
        qs = Program.objects.select_related('company')

        if _is_admin(user):
            return qs

        if has_any_role(self.request, 'ProgramOwner'):
            return qs.filter(company=user)

        if has_any_role(self.request, 'Researcher'):
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

        if has_any_role(self.request, 'Triager'):
            return qs.filter(status='active')

        return qs.none()

    def get_object(self):
        # Use get_queryset() so visibility rules (researcher/owner/admin scoping)
        # are respected for individual object retrieval, not just list views.
        # Then check object-level permissions for ownership/write-action guards.
        obj = get_object_or_404(
            self.get_queryset()
            .select_related('company')
            .prefetch_related(
                'scopes',
                'invitations__researcher',
                'applications__researcher',
                'favorites',
            ),
            pk=self.kwargs['pk']
        )
        self.check_object_permissions(self.request, obj)
        return obj

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
        events = ScoreEvent.objects.filter(program=program)
        points = events.aggregate(total=Sum('points'), avg=Avg('points'))
        return Response({
            'total_reports': reports.count(),
            'reports_by_status': dict(
                reports.values_list('status').annotate(count=Count('id'))
            ),
            'reports_by_severity': dict(
                reports.values_list('severity').annotate(count=Count('id'))
            ),
            'total_points': points['total'] or 0,
            'avg_points': points['avg'] or 0,
            'top_researchers': list(
                events.values(username=F('researcher__username'))
                .annotate(report_count=Count('id'), total_points=Sum('points'))
                .order_by('-total_points')[:10]
            ),
            'recent_activity': list(
                reports.order_by('-created_at')[:10]
                .values('id', 'title', 'status', 'severity', 'created_at')
            ),
        })
