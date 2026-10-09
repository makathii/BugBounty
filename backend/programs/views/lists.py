from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions

from core.roles import has_any_role

from ..models import Program
from ..permissions import IsResearcher
from ..serializers import ProgramListSerializer, PublicProgramSerializer
from .programs import with_favorites_total


class ResearcherProgramListView(generics.ListAPIView):
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated, IsResearcher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['created_at', 'published_at', 'total_reports', 'total_points']
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
        return with_favorites_total(
            (public | invited | applied).distinct().select_related('company')
        )


class CompanyProgramListView(generics.ListAPIView):
    serializer_class = ProgramListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not has_any_role(self.request, 'ProgramOwner'):
            return Program.objects.none()
        return with_favorites_total(
            Program.objects.filter(company=self.request.user).select_related('company')
        )


class PublicProgramListView(generics.ListAPIView):
    serializer_class = PublicProgramSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scope_type']
    search_fields = ['name', 'description', 'short_description', 'company__username']
    ordering_fields = ['published_at', 'total_reports', 'total_points']
    ordering = ['-published_at']

    def get_queryset(self):
        return Program.objects.filter(
            scope_type__in=['public', 'vdp'], status='active'
        ).select_related('company')
