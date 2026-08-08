from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import ProfileForm
from .models import AuditLog, LoginAttempt, Profile

User = get_user_model()


@role_required('admin', 'manager')
def security_center(request):
    """
    The audit trail + login-attempt monitor. This is the single most
    important screen a 'digital account management platform' needs and the
    one thing conspicuously missing from the original build: proof of who
    did what, and visibility into attacks against the login form.
    """
    logs = AuditLog.objects.select_related('user').all()
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)

    q = request.GET.get('q')
    if q:
        logs = logs.filter(username_snapshot__icontains=q)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    recent_failed_logins = LoginAttempt.objects.filter(successful=False).order_by('-created_at')[:15]

    window_start = timezone.now() - timezone.timedelta(minutes=30)
    failed_last_30 = LoginAttempt.objects.filter(successful=False, created_at__gte=window_start).count()

    return render(request, 'accounts/security_center.html', {
        'page_obj': page_obj,
        'action_choices': AuditLog.Action.choices,
        'active_filter': action_filter or '',
        'query': q or '',
        'recent_failed_logins': recent_failed_logins,
        'failed_last_30': failed_last_30,
    })


@role_required('admin')
def account_directory(request):
    """Admin-only roster of every account: role, status, last login, activity."""
    users = User.objects.select_related('profile').all().order_by('username')

    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)

    q = request.GET.get('q')
    if q:
        users = users.filter(username__icontains=q)

    return render(request, 'accounts/account_directory.html', {
        'users': users,
        'role_choices': User.ROLE_CHOICES,
        'active_role': role_filter or '',
        'query': q or '',
    })


@role_required('admin')
@require_POST
def update_account(request, user_id):
    """Change a managed account's role or status — the core RBAC admin action."""
    target = get_object_or_404(User, pk=user_id)
    profile, _ = Profile.objects.get_or_create(user=target)

    new_role = request.POST.get('role')
    new_status = request.POST.get('status')
    changed = []

    if new_role and new_role != target.role and new_role in dict(User.ROLE_CHOICES):
        old_role = target.role
        target.role = new_role
        target.save(update_fields=['role'])
        changed.append(f"role {old_role or '—'} → {new_role}")
        AuditLog.objects.create(
            user=request.user, username_snapshot=request.user.get_username(),
            action=AuditLog.Action.ROLE_CHANGED,
            detail=f"Changed {target.username}'s role: {old_role or '—'} → {new_role}",
        )

    if new_status and new_status != profile.status and new_status in dict(Profile.Status.choices):
        profile.status = new_status
        profile.save(update_fields=['status'])
        changed.append(f"status → {new_status}")

    if changed:
        messages.success(request, f"Updated {target.username}: " + ", ".join(changed))
    else:
        messages.info(request, "No changes were made.")

    return redirect('account_directory')


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(
                user=request.user, username_snapshot=request.user.get_username(),
                action=AuditLog.Action.PROFILE_UPDATED, detail='Profile fields updated',
            )
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    my_recent_activity = AuditLog.objects.filter(user=request.user)[:10]

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
        'my_recent_activity': my_recent_activity,
    })
