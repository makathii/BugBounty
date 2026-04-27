from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import ThrottledTokenObtainPairView


def security_txt(request):
    """
    RFC 9116 — security.txt served at /.well-known/security.txt
    Tells security researchers how to report vulnerabilities in this platform.
    """
    content = (
        "Contact: security@bugbounty.example.com\n"
        "Expires: 2027-04-23T00:00:00.000Z\n"
        "Preferred-Languages: en\n"
        "Policy: https://bugbounty.example.com/vdp\n"
        "Acknowledgments: https://bugbounty.example.com/hall-of-fame\n"
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('reports.urls')),
    path('api/users/', include('users.urls')),
    path('api/programs/', include('programs.urls')),
    # RFC 9116 security contact information
    path('.well-known/security.txt', security_txt, name='security-txt'),
]