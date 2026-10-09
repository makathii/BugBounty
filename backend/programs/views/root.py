from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response



@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def program_api_root(request):
    return Response({
        'company_programs': '/api/programs/company/',
        'researcher_programs': '/api/programs/researcher/',
        'public_programs': '/api/programs/public/',
        'program_detail': '/api/programs/{id}/',
        'program_dashboard': '/api/programs/{id}/dashboard/',
        'program_scopes': '/api/programs/{id}/scopes/',
        'program_invitations': '/api/programs/{id}/invitations/',
        'program_applications': '/api/programs/{id}/applications/',
        'favorites': '/api/favorites/',
        'notifications': '/api/notifications/',
        'join_program': '/api/programs/{id}/join/',
    })
