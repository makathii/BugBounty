# programs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProgramViewSet, ScopeViewSet, ProgramInvitationViewSet,
    ProgramApplicationViewSet, ProgramFavoriteViewSet,
    ProgramNotificationViewSet,
    ResearcherProgramListView, CompanyProgramListView,
    PublicProgramListView, ProgramDashboardView, program_api_root
)

router = DefaultRouter()
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'notifications', ProgramNotificationViewSet, basename='notification')
router.register(r'favorites', ProgramFavoriteViewSet, basename='favorite')

program_router = DefaultRouter()
program_router.register(r'scopes', ScopeViewSet, basename='scope')
program_router.register(r'invitations', ProgramInvitationViewSet, basename='invitation')
program_router.register(r'applications', ProgramApplicationViewSet, basename='application')

urlpatterns = [
    path('', program_api_root, name='program-api-root'),

    # Static named routes - these are now at the correct level
    path('dashboard/', ProgramDashboardView.as_view(), name='program-dashboard'),
    path('company/', CompanyProgramListView.as_view(), name='company-programs'),
    path('researcher/', ResearcherProgramListView.as_view(), name='researcher-programs'),
    path('public/', PublicProgramListView.as_view(), name='public-programs'),

    # Dynamic routes
    path('<int:pk>/dashboard/', ProgramDashboardView.as_view(), name='program-dashboard-detail'),
    path('<int:program_pk>/', include(program_router.urls)),

    # Router-generated routes
    path('', include(router.urls)),
]