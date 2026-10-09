import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Profile(models.Model):
    ROLE_USER = "User"
    ROLE_PROGRAM_OWNER = "ProgramOwner"
    ROLE_ADMIN = "Admin"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_PROGRAM_OWNER, "Program Owner"),
        (ROLE_ADMIN, "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)  # <-- add this
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.user.username


class PasswordResetToken(models.Model):
    """
    Single-use, time-limited token for password reset.
    Expires after TOKEN_EXPIRY_HOURS hours. Deleted on use.
    """
    TOKEN_EXPIRY_HOURS = 1

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PasswordResetToken for {self.user.username}"

    @classmethod
    def create_for_user(cls, user):
        """Invalidate any previous tokens and issue a fresh one."""
        cls.objects.filter(user=user, used=False).delete()
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
        )

    def is_valid(self):
        """Token is valid if unused and created within the expiry window."""
        if self.used:
            return False
        expiry = self.created_at + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        return timezone.now() <= expiry

    def consume(self):
        """Mark token as used (call before changing password)."""
        self.used = True
        self.save(update_fields=['used'])


class AccountLockout(models.Model):
    """
    Tracks failed login attempts and enforces a temporary lockout.
    After LOCKOUT_THRESHOLD failures within LOCKOUT_WINDOW_MINUTES the account
    is locked for LOCKOUT_DURATION_MINUTES minutes.
    """
    LOCKOUT_THRESHOLD = 5          # failed attempts before lockout
    LOCKOUT_WINDOW_MINUTES = 30    # rolling window to count failures
    LOCKOUT_DURATION_MINUTES = 30  # how long the lockout lasts

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lockout')
    failed_attempts = models.PositiveIntegerField(default=0)
    last_failed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"AccountLockout({self.user.username}, attempts={self.failed_attempts})"

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        # Lock has expired — clear it
        if self.locked_until and timezone.now() >= self.locked_until:
            self.reset()
        return False

    def record_failure(self):
        """Increment failure counter; lock if threshold reached."""
        now = timezone.now()
        window_start = now - timedelta(minutes=self.LOCKOUT_WINDOW_MINUTES)

        # Reset counter if last failure was outside the rolling window
        if self.last_failed_at and self.last_failed_at < window_start:
            self.failed_attempts = 0

        self.failed_attempts += 1
        self.last_failed_at = now

        if self.failed_attempts >= self.LOCKOUT_THRESHOLD:
            self.locked_until = now + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)

        self.save(update_fields=['failed_attempts', 'last_failed_at', 'locked_until'])

    def reset(self):
        """Clear lockout state on successful login or expiry."""
        self.failed_attempts = 0
        self.last_failed_at = None
        self.locked_until = None
        self.save(update_fields=['failed_attempts', 'last_failed_at', 'locked_until'])

    @classmethod
    def get_or_create_for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj


class UserMFA(models.Model):
    """
    TOTP-based two-factor authentication for a user.
    Mandatory for Admin/Triager accounts, optional for others.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mfa')
    secret = models.CharField(max_length=64)  # Base32-encoded TOTP secret
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    # Groups that MUST have 2FA enabled before login is allowed
    REQUIRED_GROUPS = {'Admin', 'Triager'}

    def __str__(self):
        return f"MFA({'enabled' if self.is_enabled else 'disabled'}) for {self.user.username}"

    def verify_code(self, code: str) -> bool:
        """
        Verify a 6-digit TOTP code. Allows 1 step of clock drift (±30 s).
        Returns True and updates last_used_at on success.
        """
        import pyotp
        totp = pyotp.TOTP(self.secret)
        valid = totp.verify(code, valid_window=1)
        if valid:
            self.last_used_at = timezone.now()
            self.save(update_fields=['last_used_at'])
        return valid

    @classmethod
    def generate_secret(cls) -> str:
        import pyotp
        return pyotp.random_base32()

    def get_provisioning_uri(self, issuer='BugBounty') -> str:
        import pyotp
        totp = pyotp.TOTP(self.secret)
        return totp.provisioning_uri(name=self.user.email, issuer_name=issuer)


class BackupCode(models.Model):
    """
    Single-use backup codes for 2FA account recovery.
    10 codes generated per user; each can only be used once.
    """
    CODES_PER_USER = 10

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash = models.CharField(max_length=128)  # SHA-256 hash of the plaintext code
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"BackupCode(user={self.user.username}, used={self.used})"

    @classmethod
    def generate_for_user(cls, user):
        """
        Generate CODES_PER_USER fresh backup codes.
        Deletes any previous codes. Returns list of plaintext codes (shown once).
        """
        import hashlib
        cls.objects.filter(user=user).delete()
        plaintext_codes = []
        for _ in range(cls.CODES_PER_USER):
            code = secrets.token_hex(5).upper()  # e.g. "A3F9B2C1D0"
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            cls.objects.create(user=user, code_hash=code_hash)
            plaintext_codes.append(code)
        return plaintext_codes

    @classmethod
    def use_code(cls, user, plaintext_code: str) -> bool:
        """Consume a backup code. Returns True if valid and unused."""
        import hashlib
        code_hash = hashlib.sha256(plaintext_code.upper().encode()).hexdigest()
        try:
            bc = cls.objects.get(user=user, code_hash=code_hash, used=False)
            bc.used = True
            bc.used_at = timezone.now()
            bc.save(update_fields=['used', 'used_at'])
            return True
        except cls.DoesNotExist:
            return False


class SocialAccount(models.Model):
    """
    Links a Django User to an OAuth provider identity.

    A user can have multiple SocialAccounts (e.g. one for GitHub, one for
    Google). The (provider, provider_uid) pair is unique — that's the only
    thing the OAuth callback uses to identify a returning user.
    """
    PROVIDER_GITHUB = 'github'
    PROVIDER_GOOGLE = 'google'
    PROVIDER_GITLAB = 'gitlab'
    PROVIDER_CHOICES = [
        (PROVIDER_GITHUB, 'GitHub'),
        (PROVIDER_GOOGLE, 'Google'),
        (PROVIDER_GITLAB, 'GitLab'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_uid = models.CharField(max_length=128, db_index=True)
    email = models.EmailField(blank=True, default='')
    raw_profile = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('provider', 'provider_uid')]
        ordering = ['-last_login_at']

    def __str__(self):
        return f"{self.provider}:{self.provider_uid} -> {self.user.username}"


class UserSession(models.Model):
    """
    Tracks active JWT sessions per user for visibility and revocation.
    Created at login, deactivated on logout or password change.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    jti = models.CharField(max_length=255, unique=True, db_index=True, help_text="JWT ID claim — links this record to a specific token pair")
    device_name = models.CharField(max_length=200, blank=True, default='Unknown device')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_active']

    def __str__(self):
        return f"{self.user.username} — {self.device_name} ({self.ip_address})"