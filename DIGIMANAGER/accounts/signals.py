import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AuditLog, LoginAttempt

security_logger = logging.getLogger('accounts.security')


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _user_agent(request):
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:255]


@receiver(user_logged_in)
def on_login_success(sender, request, user, **kwargs):
    ip = _client_ip(request)
    LoginAttempt.objects.create(username=user.get_username(), ip_address=ip, successful=True)
    AuditLog.objects.create(
        user=user,
        username_snapshot=user.get_username(),
        action=AuditLog.Action.LOGIN_SUCCESS,
        ip_address=ip,
        user_agent=_user_agent(request),
        detail='Authenticated session established',
    )
    security_logger.info("LOGIN_SUCCESS user=%s ip=%s", user.get_username(), ip)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is None:
        return
    AuditLog.objects.create(
        user=user,
        username_snapshot=user.get_username(),
        action=AuditLog.Action.LOGOUT,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    security_logger.info("LOGOUT user=%s", user.get_username())


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    username = credentials.get('username', 'unknown')
    ip = _client_ip(request)
    LoginAttempt.objects.create(username=username, ip_address=ip, successful=False)
    AuditLog.objects.create(
        user=None,
        username_snapshot=username,
        action=AuditLog.Action.LOGIN_FAILED,
        ip_address=ip,
        user_agent=_user_agent(request),
        detail='Invalid credentials submitted',
    )
    security_logger.warning("LOGIN_FAILED username=%s ip=%s", username, ip)
