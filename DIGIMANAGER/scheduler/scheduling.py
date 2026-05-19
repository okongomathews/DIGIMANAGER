import json
from django_celery_beat.models import ClockedSchedule, PeriodicTask

def schedule_post(post):
    clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=post.scheduled_time)

    PeriodicTask.objects.create(
        clocked=clocked,
        name=f"Publish Post {post.id}",
        task='scheduler.tasks.publish_scheduled_post',
        args=json.dumps([post.id]),
        one_off=True
    )