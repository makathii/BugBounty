from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Company
from ..serializers import CompanySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"companies": serializer.data})

    @action(detail=False, methods=['get'])
    def has_profile(self, request):
        return Response({
            "has_company_profile": Company.objects.filter(user=request.user).exists()
        })

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        company = Company.objects.filter(user=request.user).first()
        if company is None:
            return Response(
                {"detail": "No company profile found."},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(self.get_serializer(company).data)
