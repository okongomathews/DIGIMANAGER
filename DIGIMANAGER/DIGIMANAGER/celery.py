import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DIGIMANAGER.settings')

app = Celery('DIGIMANAGER')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'auto-publish-posts-every-minute': {
        'task': 'scheduler.tasks.auto_publish_scheduled_posts',
        'schedule': crontab(),  # every minute
    },
}
