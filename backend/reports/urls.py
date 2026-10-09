from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BugReportViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'reports', BugReportViewSet, basename='report')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]
