from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import AuditLog


def role_required(*allowed_roles):
    """
    Function-view decorator enforcing RBAC centrally instead of the
    `if request.user.role != 'admin': redirect(...)` pattern repeated
    ad hoc across views. Denials are audited, not just silently redirected.

    Usage:
        @role_required('admin', 'manager')
        def some_view(request): ...
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if getattr(request.user, 'role', None) not in allowed_roles:
                AuditLog.objects.create(
                    user=request.user,
                    username_snapshot=request.user.get_username(),
                    action=AuditLog.Action.PERMISSION_DENIED,
                    path=request.path[:255],
                    method=request.method,
                    detail=f"Required role in {allowed_roles}, had '{getattr(request.user, 'role', None)}'",
                )
                messages.error(request, "You don't have permission to view that page.")
                return redirect('unauthorized')
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
