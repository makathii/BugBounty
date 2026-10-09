from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Program, ProgramApplication
from ..permissions import _can_manage
from ..serializers import ProgramApplicationSerializer


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
