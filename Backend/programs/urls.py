from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProgramViewSet, ScopeViewSet, ProgramInvitationViewSet,
    ProgramApplicationViewSet, ProgramFavoriteViewSet,
    ResearcherProgramListView, CompanyProgramListView,
    PublicProgramListView, ProgramDashboardView, program_api_root
)

router = DefaultRouter()
router.register(r'programs', ProgramViewSet, basename='program')

# Nested routes for program-specific resources
program_router = DefaultRouter()
program_router.register(r'scopes', ScopeViewSet, basename='scope')
program_router.register(r'invitations', ProgramInvitationViewSet, basename='invitation')
program_router.register(r'applications', ProgramApplicationViewSet, basename='application')

# Separate router for favorites
favorite_router = DefaultRouter()
favorite_router.register(r'favorites', ProgramFavoriteViewSet, basename='favorite')

urlpatterns = [
    # Program management
    path('', include(router.urls)),

    # Program-specific routes
    path('programs/<int:program_pk>/', include(program_router.urls)),

    # Dashboard
    path('programs/dashboard/', ProgramDashboardView.as_view(), name='program-dashboard'),
    path('programs/<int:pk>/dashboard/', ProgramDashboardView.as_view(), name='program-dashboard-detail'),

    # Program lists by role
    path('programs/company/', CompanyProgramListView.as_view(), name='company-programs'),
    path('programs/researcher/', ResearcherProgramListView.as_view(), name='researcher-programs'),
    path('programs/public/', PublicProgramListView.as_view(), name='public-programs'),

    # Favorites
    path('favorites/', include(favorite_router.urls)),

    # API root
    path('', program_api_root, name='program-api-root'),
]