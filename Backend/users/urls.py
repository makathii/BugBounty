from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .views import UserRegistrationView, UserProfileView, user_groups, verify_email, logout, resend_verification_email
from programs.views import CompanyViewSet


@api_view(['GET'])
@permission_classes([AllowAny])
def users_api_root(request):
    return Response({
        'register': '/api/users/register/',
        'profile': '/api/users/profile/',
        'groups': '/api/users/groups/',
        'verify_email': '/api/users/verify-email/{token}/',
    })

urlpatterns = [
    path('', users_api_root, name='users-api-root'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('groups/', user_groups, name='user-groups'),
    path('logout/', logout, name='logout'),
    path('verify-email/<str:token>/', verify_email, name='verify-email'),
    path('resend-verification/', resend_verification_email, name='resend-verification'),
    path('companies/', CompanyViewSet.as_view({'post': 'create', 'get': 'list'}), name='user-companies'),
]
