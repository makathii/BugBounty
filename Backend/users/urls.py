from django.urls import path
from .views import UserRegistrationView, UserProfileView, user_groups, users_api_root
from .views import verify_email

urlpatterns = [
path('', users_api_root, name='users-api-root'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('groups/', user_groups, name='user-groups'),
    path("verify-email/<str:token>/", verify_email),
]