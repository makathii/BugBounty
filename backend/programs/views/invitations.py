from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Program, ProgramInvitation
from ..permissions import _can_manage
from ..serializers import ProgramInvitationSerializer


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
