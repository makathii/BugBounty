from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import UserSession


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """
    GET /api/users/sessions/
    Returns all active sessions for the current user.
    """
    sessions = UserSession.objects.filter(user=request.user, is_active=True)
    data = [
        {
            'id': s.id,
            'device_name': s.device_name,
            'ip_address': s.ip_address,
            'created_at': s.created_at,
            'last_active': s.last_active,
        }
        for s in sessions
    ]
    return Response({'sessions': data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def revoke_session(request, session_id):
    """
    DELETE /api/users/sessions/<id>/
    Revokes a specific session belonging to the current user.
    """
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
    except UserSession.DoesNotExist:
        return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

    session.is_active = False
    session.save(update_fields=['is_active'])
    return Response({'detail': 'Session revoked.'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def revoke_all_sessions(request):
    """
    DELETE /api/users/sessions/revoke-all/
    Revokes all active sessions for the current user (logout everywhere).
    """
    count = UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
    return Response({'detail': f'Revoked {count} session(s).'}, status=status.HTTP_200_OK)
