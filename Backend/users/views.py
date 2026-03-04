from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User, Group
from .serializers import UserSerializer, UserRegistrationSerializer
from .throttles import LoginThrottle, RegisterThrottle
from rest_framework.permissions import AllowAny
from .models import Profile

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Assign to Researcher group by default
        try:
            researcher_group = Group.objects.get(name='Researcher')
            user.groups.add(researcher_group)
        except Group.DoesNotExist:
            # Create the group if it doesn't exist
            researcher_group = Group.objects.create(name='Researcher')
            user.groups.add(researcher_group)

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "User created successfully"
            },
            status=status.HTTP_201_CREATED
        )


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_groups(request):
    # Get current user's groups
    groups = request.user.groups.values_list('name', flat=True)
    return Response({"groups": list(groups)})

# users/views.py
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data["refresh_token"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out"}, status=200)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=400)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def users_api_root(request):
    return Response({
        'register': '/api/users/register/',
        'profile': '/api/users/profile/',
        'groups': '/api/users/groups/'
    })

# Override TokenObtainPairView to add throttling
from rest_framework_simplejwt.views import TokenObtainPairView

class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]

#Email verification
@api_view(["GET"])
@permission_classes([AllowAny])
def verify_email(request, token):
    try:
        profile = Profile.objects.get(email_verification_token=token)
        profile.email_verified = True
        profile.email_verification_token = None
        profile.save()
        return Response({"detail": "Email verified successfully"})
    except Profile.DoesNotExist:
        return Response({"detail": "Invalid or expired token"}, status=400)