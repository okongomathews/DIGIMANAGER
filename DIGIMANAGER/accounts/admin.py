from django.contrib import admin
from .models import AuditLog, LoginAttempt, Profile


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username_snapshot', 'action', 'method', 'path', 'ip_address', 'status_code')
    list_filter = ('action', 'method')
    search_fields = ('username_snapshot', 'path', 'ip_address')
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False  # audit rows are system-generated only


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username', 'ip_address', 'successful')
    list_filter = ('successful',)
    search_fields = ('username', 'ip_address')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'status', 'two_factor_enabled', 'updated_at')
    list_filter = ('status', 'department')
    search_fields = ('user__username', 'user__email')
