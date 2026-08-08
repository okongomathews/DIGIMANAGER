from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """
    Append-only record of security-relevant and state-changing activity.
    This is the backbone of 'account management best practice' #1: every
    login, logout, permission failure, and write operation is attributable
    to a specific account, at a specific time, from a specific origin.
    """

    class Action(models.TextChoices):
        LOGIN_SUCCESS = 'login_success', 'Login succeeded'
        LOGIN_FAILED = 'login_failed', 'Login failed'
        LOGOUT = 'logout', 'Logout'
        ACCOUNT_LOCKED = 'account_locked', 'Account temporarily locked'
        PASSWORD_CHANGED = 'password_changed', 'Password changed'
        PROFILE_UPDATED = 'profile_updated', 'Profile updated'
        ROLE_CHANGED = 'role_changed', 'Role changed'
        PERMISSION_DENIED = 'permission_denied', 'Permission denied'
        REQUEST = 'request', 'State-changing request'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries',
    )
    # kept even if the account is later deleted, so the trail survives
    username_snapshot = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=32, choices=Action.choices, default=Action.REQUEST)
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        who = self.username_snapshot or 'anonymous'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {who} — {self.get_action_display()}"


class LoginAttempt(models.Model):
    """
    Tracks every authentication attempt (successful or not) keyed by the
    submitted username + source IP. Used to enforce a lockout window and
    to give admins visibility into credential-stuffing / brute-force
    patterns without needing a third-party package.
    """

    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = 'success' if self.successful else 'failure'
        return f"{self.username} @ {self.ip_address} — {status}"


class Profile(models.Model):
    """
    Extends CustomUser without touching its migration history. Holds the
    account-management fields a real admin console needs: contact details,
    department/team, status, and a lightweight 2FA readiness flag.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        PENDING = 'pending', 'Pending verification'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    phone_number = models.CharField(max_length=32, blank=True)
    department = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=255, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text='Foundation flag for TOTP-based 2FA; wire up a verification view before enabling in production.',
    )
    last_password_change = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"

    @property
    def is_active_account(self):
        return self.status == self.Status.ACTIVE
