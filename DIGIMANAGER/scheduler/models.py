from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser



class Platform(models.Model):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter (X)'),
        ('linkedin', 'LinkedIn'),
    ]
    name = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='instagram')
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_in = models.IntegerField(blank=True, null=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name.title()} - {self.added_by.username}"


class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    content = models.TextField()  # Can be AI-generated
    image = models.ImageField(upload_to='', null=True, blank=True)  # Optional manual upload
    scheduled_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    generated_caption_by = models.CharField(max_length=100, blank=True, null=True)  # e.g., 'gpt-4'
    generated_image_by = models.CharField(max_length=100, blank=True, null=True)    # e.g., 'dall-e-2'

    def __str__(self):
        return f"{self.user.username} - {self.platform.name} - {self.status}"


class AIGeneratedAsset(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='ai_assets')
    asset_type = models.CharField(max_length=10, choices=[('image', 'Image'), ('caption', 'Caption')])
    source_model = models.CharField(max_length=100)  # 'gpt-4.1', 'dall-e-2', 'stable-diffusion-v1.5', etc.
    generation_prompt = models.TextField()
    output_data = models.TextField(help_text="Base64 string or image URL")
    file = models.ImageField(upload_to='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset_type} by {self.source_model} for Post ID {self.post.id}"


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('creator', 'Content Creator'),
        ('manager', 'Manager'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

class ContentPrompt(models.Model):
    prompt = models.TextField()
    generated_caption = models.TextField()
    tone = models.CharField(max_length=50, choices=[
        ('formal', 'Formal'),
        ('humorous', 'Humorous'),
        ('promotional', 'Promotional'),
        ('informative', 'Informative'),
    ])
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE,related_name='contentprompts_scheduler')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='contentprompts_scheduler')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.prompt[:50]}..."


class Content(models.Model):
    ...
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)        