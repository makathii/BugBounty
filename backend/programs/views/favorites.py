from rest_framework import permissions, serializers as drf_serializers, viewsets

from ..models import ProgramFavorite
from ..permissions import CanAccessProgram, IsResearcher
from ..serializers import ProgramFavoriteSerializer


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
