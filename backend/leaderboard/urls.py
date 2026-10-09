from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LeaderboardViewSet, LevelViewSet

router = DefaultRouter()
router.register(r"leaderboard", LeaderboardViewSet, basename="leaderboard")
router.register(r"levels", LevelViewSet, basename="levels")

urlpatterns = [
    path("", include(router.urls)),
]
