from .models import AuditLog

# Paths we don't want to spam the log with (static/media/health checks).
_EXCLUDED_PREFIXES = ('/static/', '/media/', '/admin/jsi18n/')
_LOGGED_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


class AuditLogMiddleware:
    """
    Belt-and-braces logging layer: signals.py covers auth events, this
    covers *what an authenticated account changed*. It never blocks the
    request — logging failures are swallowed so audit infrastructure can
    never take the app down.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception:
            pass
        return response

    def _maybe_log(self, request, response):
        if request.method not in _LOGGED_METHODS:
            return
        if request.path.startswith(_EXCLUDED_PREFIXES):
            return
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return

        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')

        AuditLog.objects.create(
            user=user,
            username_snapshot=user.get_username(),
            action=AuditLog.Action.REQUEST,
            path=request.path[:255],
            method=request.method,
            status_code=getattr(response, 'status_code', None),
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        )
