from django.db import models
from django.contrib.auth import get_user_model
from scheduler.models import Platform

User = get_user_model()

class ContentPrompt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='contentprompts_contentgen')
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE,related_name='contentprompts_contentgen')
    prompt = models.TextField()
    tone = models.CharField(max_length=50, choices=[
        ('formal', 'Formal'),
        ('humorous', 'Humorous'),
        ('promotional', 'Promotional'),
    ], default='formal')
    generated_caption = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prompt by {self.user.username} on {self.created_at.date()}"