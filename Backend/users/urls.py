from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .views import (
    UserRegistrationView, UserProfileView, user_groups,
    verify_email, logout, resend_verification_email,
    PasswordResetRequestView, PasswordResetConfirmView,
    list_sessions, revoke_session, revoke_all_sessions,
    mfa_setup, mfa_confirm, mfa_disable, mfa_status, mfa_regenerate_backup_codes,
    CSRFTokenView,
)
from .oauth_views import oauth_start, oauth_callback
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
    path('companies/has_profile/', CompanyViewSet.as_view({'get': 'has_profile'}), name='user-companies-has-profile'),
    path('companies/my_profile/', CompanyViewSet.as_view({'get': 'my_profile'}), name='user-companies-my-profile'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('sessions/', list_sessions, name='session-list'),
    path('sessions/revoke-all/', revoke_all_sessions, name='session-revoke-all'),
    path('sessions/<int:session_id>/', revoke_session, name='session-revoke'),
    path('mfa/setup/', mfa_setup, name='mfa-setup'),
    path('mfa/confirm/', mfa_confirm, name='mfa-confirm'),
    path('mfa/disable/', mfa_disable, name='mfa-disable'),
    path('mfa/status/', mfa_status, name='mfa-status'),
    path('mfa/backup-codes/', mfa_regenerate_backup_codes, name='mfa-backup-codes'),
    # CSRF token endpoint — React calls this once on app load to seed the
    # csrftoken cookie before making any state-changing call.
    path('csrf/', CSRFTokenView.as_view(), name='csrf-token'),
    # OAuth client login (GitHub / Google / GitLab).
    path('oauth/<str:provider>/start/', oauth_start, name='oauth-start'),
    path('oauth/<str:provider>/callback/', oauth_callback, name='oauth-callback'),
]
