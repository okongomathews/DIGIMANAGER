from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AIGeneratedAsset, ContentPrompt, CustomUser, Platform, Post

# Register your models here.

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'is_staff']

admin.site.register(ContentPrompt)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Platform)
admin.site.register(Post)
admin.site.register(AIGeneratedAsset)