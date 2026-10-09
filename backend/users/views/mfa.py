from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..mfa_enrollment import InvalidEnrollmentToken, user_for_enrollment_token
from ..models import BackupCode, UserMFA
from ..throttles import MfaCodeThrottle, MfaEnrollThrottle


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_setup(request):
    """
    POST /api/users/mfa/setup/
    Generates a new TOTP secret and provisioning URI (QR code data).
    Does NOT enable 2FA yet — user must confirm with a valid code first.
    """
    mfa, _ = UserMFA.objects.get_or_create(
        user=request.user,
        defaults={'secret': UserMFA.generate_secret()},
    )
    if not mfa.is_enabled:
        # (Re)generate secret for fresh setup
        mfa.secret = UserMFA.generate_secret()
        mfa.save(update_fields=['secret'])

    return Response({
        'secret': mfa.secret,
        'provisioning_uri': mfa.get_provisioning_uri(),
        'message': 'Scan the QR code with your authenticator app, then confirm with POST /api/users/mfa/confirm/',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([MfaCodeThrottle])
def mfa_confirm(request):
    """
    POST /api/users/mfa/confirm/  { "code": "123456" }
    Verifies the first TOTP code and activates 2FA. Also generates backup codes.
    """
    code = request.data.get('code')
    if not code:
        return Response({'detail': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mfa = request.user.mfa
    except UserMFA.DoesNotExist:
        return Response({'detail': 'Run /api/users/mfa/setup/ first.'}, status=status.HTTP_400_BAD_REQUEST)

    if not mfa.verify_code(str(code)):
        return Response({'detail': 'Invalid code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

    mfa.is_enabled = True
    mfa.save(update_fields=['is_enabled'])

    backup_codes = BackupCode.generate_for_user(request.user)

    return Response({
        'detail': '2FA enabled successfully.',
        'backup_codes': backup_codes,
        'warning': 'Save these backup codes securely. They will not be shown again.',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([MfaCodeThrottle])
def mfa_disable(request):
    """
    POST /api/users/mfa/disable/  { "code": "123456" }
    Disables 2FA after verifying the current TOTP code (or a backup code).
    """
    code = request.data.get('code')
    if not code:
        return Response({'detail': 'code is required to disable 2FA.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mfa = request.user.mfa
    except UserMFA.DoesNotExist:
        return Response({'detail': '2FA is not set up on this account.'}, status=status.HTTP_400_BAD_REQUEST)

    if not mfa.is_enabled:
        return Response({'detail': '2FA is already disabled.'}, status=status.HTTP_400_BAD_REQUEST)

    # Must be a required-group member — they cannot disable 2FA
    user_groups_set = set(request.user.groups.values_list('name', flat=True))
    if UserMFA.REQUIRED_GROUPS & user_groups_set:
        return Response(
            {'detail': '2FA cannot be disabled for Admin/Triager accounts.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not mfa.verify_code(str(code)) and not BackupCode.use_code(request.user, str(code)):
        return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

    mfa.is_enabled = False
    mfa.save(update_fields=['is_enabled'])
    BackupCode.objects.filter(user=request.user).delete()

    return Response({'detail': '2FA has been disabled.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([MfaCodeThrottle])
def mfa_regenerate_backup_codes(request):
    """
    POST /api/users/mfa/backup-codes/  { "code": "123456" }
    Replaces all backup codes with a fresh set. Requires a current TOTP code
    (a backup code is deliberately not accepted: it would let one leaked code
    mint ten more). The new plaintext codes are returned once.
    """
    code = request.data.get('code')
    if not code:
        return Response({'detail': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mfa = request.user.mfa
    except UserMFA.DoesNotExist:
        return Response({'detail': '2FA is not enabled on this account.'}, status=status.HTTP_400_BAD_REQUEST)
    if not mfa.is_enabled:
        return Response({'detail': '2FA is not enabled on this account.'}, status=status.HTTP_400_BAD_REQUEST)

    if not mfa.verify_code(str(code)):
        return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'detail': 'New backup codes generated. Previous codes no longer work.',
        'backup_codes': BackupCode.generate_for_user(request.user),
    })


def _enrollment_user(request):
    token = request.data.get('enrollment_token')
    if not token:
        raise InvalidEnrollmentToken('enrollment_token is required.')
    return user_for_enrollment_token(str(token))


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([MfaEnrollThrottle])
def mfa_enroll_setup(request):
    """
    POST /api/users/mfa/enroll/setup/  { "enrollment_token": "..." }
    Pre-login twin of mfa_setup for Admin/Triager accounts that must enroll
    before they can sign in. Returns a fresh secret + provisioning URI.
    """
    try:
        user = _enrollment_user(request)
    except InvalidEnrollmentToken as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    mfa, _ = UserMFA.objects.get_or_create(user=user, defaults={'secret': UserMFA.generate_secret()})
    mfa.secret = UserMFA.generate_secret()
    mfa.save(update_fields=['secret'])
    return Response({'secret': mfa.secret, 'provisioning_uri': mfa.get_provisioning_uri()})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([MfaEnrollThrottle])
def mfa_enroll_confirm(request):
    """
    POST /api/users/mfa/enroll/confirm/  { "enrollment_token": "...", "code": "123456" }
    Verifies the first TOTP code, enables 2FA and returns the backup codes once.
    Issues no login tokens: the user signs in afterwards with a code.
    """
    try:
        user = _enrollment_user(request)
    except InvalidEnrollmentToken as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    code = request.data.get('code')
    if not code:
        return Response({'detail': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

    mfa = UserMFA.objects.filter(user=user).first()
    if mfa is None:
        return Response({'detail': 'Start the setup first.'}, status=status.HTTP_400_BAD_REQUEST)
    if not mfa.verify_code(str(code)):
        return Response({'detail': 'Invalid code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

    mfa.is_enabled = True
    mfa.save(update_fields=['is_enabled'])
    return Response({
        'detail': '2FA enabled successfully. You can now sign in.',
        'backup_codes': BackupCode.generate_for_user(user),
        'warning': 'Save these backup codes securely. They will not be shown again.',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mfa_status(request):
    """
    GET /api/users/mfa/status/
    Returns 2FA setup status for the current user.
    """
    try:
        mfa = request.user.mfa
        enabled = mfa.is_enabled
    except UserMFA.DoesNotExist:
        enabled = False

    user_groups_set = set(request.user.groups.values_list('name', flat=True))
    required = bool(UserMFA.REQUIRED_GROUPS & user_groups_set)

    return Response({
        'is_enabled': enabled,
        'is_required': required,
        'backup_codes_remaining': BackupCode.objects.filter(
            user=request.user, used=False
        ).count() if enabled else 0,
    })
