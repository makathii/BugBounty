from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User, Group

from .serializers import UserSerializer, UserRegistrationSerializer
from .throttles import LoginThrottle, RegisterThrottle
from .models import Profile


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

# TODO
        role = serializer.validated_data.get('role', 'researcher')
        group_name = 'Company' if role == 'company' else 'Researcher'

        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "User created successfully. Please check your email to verify your account.",
            },
            status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_groups(request):
    groups = list(request.user.groups.values_list('name', flat=True))
    return Response({
        "groups": groups,
        "is_researcher": 'Researcher' in groups,
        "is_company": 'Company' in groups,
        "is_triager": 'Triager' in groups,
        "is_admin": request.user.is_superuser or 'Admin' in groups,
    })


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "refresh_token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out"})
    except Exception:
        return Response(
            {"error": "Invalid or expired token"},
            status=status.HTTP_400_BAD_REQUEST
        )


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    try:
        profile = Profile.objects.get(email_verification_token=token)
        profile.email_verified = True
        profile.email_verification_token = None
        profile.save()
        return Response({"detail": "Email verified successfully."})
    except Profile.DoesNotExist:
        return Response(
            {"detail": "Invalid or expired verification token."},
            status=status.HTTP_400_BAD_REQUEST
        )


# ---------------------------------------------------------------------------
# API root
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def users_api_root(request):
    return Response({
        'register': '/api/users/register/',
        'profile': '/api/users/profile/',
        'groups': '/api/users/groups/',
        'logout': '/api/users/logout/',
        'verify_email': '/api/users/verify-email/{token}/',
    })


# ---------------------------------------------------------------------------
# Throttled login
# ---------------------------------------------------------------------------

class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]