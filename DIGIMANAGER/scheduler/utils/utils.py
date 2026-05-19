import shutil, os
from django.conf import settings
from django.core.mail import send_mail

def cleanup_temp_images():
    temp_dir = os.path.join(settings.MEDIA_ROOT, "ai_temp")
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

def send_post_notification(user_email, subject, message):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
