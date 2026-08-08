from .models import Profile


def nav_context(request):
    """
    Makes the sidebar/topbar role-aware and profile-aware in every template
    without every view having to remember to pass it in.
    """
    ctx = {'current_profile': None}
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=user)
        ctx['current_profile'] = profile
    return ctx
