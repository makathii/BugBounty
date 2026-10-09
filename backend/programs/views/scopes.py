from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets

from ..models import Program, Scope
from ..permissions import IsProgramOwnerOrAdmin
from ..serializers import ScopeSerializer


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
