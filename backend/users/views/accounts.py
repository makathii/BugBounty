from django.contrib.auth.models import Group, User
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from reports.captcha import verify_recaptcha

from ..serializers import UserRegistrationSerializer, UserSerializer
from ..throttles import RegisterThrottle


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        # Validate reCAPTCHA
        captcha_token = request.data.get('captcha')
        try:
            verify_recaptcha(captcha_token, request.META.get('REMOTE_ADDR'))
        except Exception as e:
            return Response({"captcha": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        role = serializer.validated_data.get('role', 'researcher')
        group_name = 'ProgramOwner' if role == 'company' else 'Researcher'

        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "Registration successful. Please check your email to verify your account before logging in."
            },
            status=status.HTTP_201_CREATED
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_groups(request):
    groups = list(request.user.groups.values_list('name', flat=True))
    return Response({
        "groups": groups,
        "is_researcher": 'Researcher' in groups,
        "is_company": 'ProgramOwner' in groups,
        "is_program_owner": 'ProgramOwner' in groups,
        "is_triager": 'Triager' in groups,
        "is_admin": request.user.is_superuser or 'Admin' in groups,
    })
