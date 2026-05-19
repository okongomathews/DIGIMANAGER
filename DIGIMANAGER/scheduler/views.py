import base64
import os
import calendar
from io import BytesIO
from datetime import timedelta

import torch
from diffusers import StableDiffusionPipeline
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.crypto import get_random_string
from django.db.models import Count
from PIL import Image, ImageDraw

from .forms import RegisterForm, PostForm, ContentPromptForm, PlatformForm
from .models import Content, ContentPrompt, Post, Platform
from .tasks import publish_scheduled_post
from .aiUtils import generateCaptionAi
from .utils.aiGeneration import generate_dalle_image, refine_image_gpt4, generate_image_sd
from django.views.decorators.http import require_POST
from django.core.files import File
import logging

from urllib.request import urlretrieve
from urllib.parse import urlparse

from .scheduling import schedule_post

from .utils.utils import cleanup_temp_images
from django.core.mail import send_mail

from collections import defaultdict


import openpyxl
from xhtml2pdf import pisa
from django.template.loader import get_template

import json
from django_celery_beat.models import PeriodicTask, ClockedSchedule

import openpyxl

#######################
# AI IMAGE GENERATION #
#######################

@require_POST
@csrf_exempt
def generate_ai_image(request, post_id=None):
    caption = request.POST.get("caption")
    model = request.POST.get("model", "dalle")

    if not caption or not model:
        return JsonResponse({"error": "Missing caption or model."}, status=400)

    try:
        # Simulate or generate image
        if model == "stablediffusion":
            try:
                # Placeholder logic for actual Stable Diffusion model
                image = Image.new('RGB', (600, 400), color='lightblue')
                draw = ImageDraw.Draw(image)
                draw.text((10, 180), f"SD: {caption}", fill='black')
            except Exception:
                return JsonResponse({"image_url": "https://dummyimage.com/600x400/cccccc/000000&text=AI+Unavailable"})
        else:
            # Default model (e.g. DALL·E simulation)
            image = Image.new('RGB', (600, 400), color='lightgray')
            draw = ImageDraw.Draw(image)
            draw.text((10, 180), f"{model.upper()}: {caption}", fill='black')

        # Save generated image to buffer
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"{uuid.uuid4()}.png"
        relative_path = f"ai_temp/{filename}"
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # Write image to disk
        with open(absolute_path, "wb") as f:
            f.write(buffer.getvalue())

        image_url = settings.MEDIA_URL + relative_path

        # If post ID is provided, save image to the post
        if post_id:
            try:
                post = Post.objects.get(id=post_id)
                # Move image to permanent location
                final_rel_path = f"posts/{filename}"
                final_abs_path = os.path.join(settings.MEDIA_ROOT, final_rel_path)
                os.makedirs(os.path.dirname(final_abs_path), exist_ok=True)
                os.rename(absolute_path, final_abs_path)

                post.image.name = final_rel_path  # store relative path
                post.save()

                image_url = settings.MEDIA_URL + final_rel_path
            except Post.DoesNotExist:
                return JsonResponse({"error": "Post not found."}, status=404)

        return JsonResponse({"image_url": image_url})

    except Exception as e:
        return JsonResponse({"error": "Unexpected server error.", "details": str(e)}, status=500)


@login_required
def refine_ai_image(request):
    if request.method == 'POST':
        raw_prompt = request.POST.get('prompt')
        refined_prompt = ai_prompt_enhancer(raw_prompt)  # Optional NLP enhancer
        refined_image = generate_image_from_prompt(refined_prompt)
        return render(request, 'ai/refine_result.html', {'image': refined_image, 'prompt': refined_prompt})
    return render(request, 'ai/refine.html')


def generate_image_sd(prompt):
    model_id = "stabilityai/stable-diffusion-2-1"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        cache_dir=settings.HUGGINGFACE_CACHE_DIR
    ).to(device)

    result = pipe(prompt, num_inference_steps=50).images[0]

    filename = f"{uuid.uuid4()}.png"
    image_path = os.path.join(settings.MEDIA_ROOT, "generated", filename)
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    result.save(image_path)

    return image_path  # Returns absolute path; convert to URL in view


##########
# AUTH   #
##########

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome {user.username}!")

            if user.role == 'admin':
                return redirect('admDashboard')
            elif user.role == 'creator':
                return redirect('creatorDashboard')
            elif user.role == 'manager':
                return redirect('managerDashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def logout(request):
    auth_logout(request)
    messages.info(request, "Log out successful.")
    return redirect('login')


####################
# CAPTION GENERATOR#
####################

@login_required
def generateCaption(request):
    caption = None
    if request.method == 'POST':
        form = ContentPromptForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.generated_caption = generateCaptionAi(obj.prompt, obj.tone)
            obj.status = 'draft'
            obj.save()
            caption = obj
            messages.success(request, "Caption generated and saved as draft.")
    else:
        form = ContentPromptForm()
    return render(request, 'scheduler/generateCaption.html', {'form': form, 'caption': caption})

@login_required
def captionHistory(request):
    captions = ContentPrompt.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'scheduler/captionHistory.html', {'captions': captions})


###############
# POSTS       #
###############
@login_required
def createPost(request):
    if request.user.role != 'creator':
        return redirect('unauthorized')

    if request.method == 'GET':
        cleanup_temp_images()

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)

        ai_image_url = request.POST.get('ai_image_url')

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.status = request.POST.get('status', 'draft')

            # Handle AI-generated image if uploaded manually or via AI
            if not request.FILES.get('image') and ai_image_url:
                try:
                    parsed_url = urlparse(ai_image_url)
                    filename = os.path.basename(parsed_url.path)
                    temp_path = os.path.join(settings.MEDIA_ROOT, 'ai_temp', filename)

                    if os.path.exists(temp_path):
                        final_path = os.path.join(settings.MEDIA_ROOT, 'posts', filename)
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        os.rename(temp_path, final_path)

                        post.image.name = f'posts/{filename}'
                    else:
                        messages.warning(request, "AI-generated image not found in temp storage.")
                except Exception as e:
                    messages.error(request, f"Error processing AI image: {str(e)}")

            post.save()

            #  Removed publishPost.apply_async()
            # Post will now go to scheduled → manager approves → published

            messages.success(request, "Post saved successfully.")
            return redirect('creatorDashboard')
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        form = PostForm()

    return render(request, 'posts/createPost.html', {'form': form})

@login_required
def myPosts(request):
    posts = Post.objects.filter(user=request.user)
    return render(request, 'posts/postList.html', {'posts': posts})

@login_required
def viewPost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.user and request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')
    return render(request, 'posts/postDetail.html', {'post': post})


@login_required
def editPost(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    # Ensure only the post creator can edit
    if request.user.id != post.user_id:
        return redirect('unauthorized')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)

            # Handle AI-generated image URL if provided
            ai_image_url = request.POST.get('ai_image_url')
            if ai_image_url:
                updated_post.image = ai_image_url  # Optional: convert to ImageField if needed

            updated_post.save()

            # Schedule task if post is to be scheduled
            if updated_post.status == 'scheduled':
                task_name = f"publish_post_{updated_post.id}"

                # Remove any existing periodic task with the same name
                PeriodicTask.objects.filter(name=task_name).delete()

                # Create or reuse ClockedSchedule for the exact time
                clocked_time = updated_post.scheduled_time
                clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=clocked_time)

                # Register new Celery periodic task
                PeriodicTask.objects.create(
                    name=task_name,
                    task='scheduler.tasks.publish_post',  # Replace with your Celery task path
                    clocked=clocked,
                    one_off=True,
                    args=json.dumps([updated_post.id]),
                    start_time=clocked_time,
                    enabled=True,
                )

            messages.success(request, "✅ Post updated successfully.")
            return redirect('viewPost', post_id=updated_post.pk)

    else:
        form = PostForm(instance=post)

    context = {
        'form': form,
        'post': post,
    }
    return render(request, 'posts/createPost.html', context)

@login_required
def deletePost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user == post.user:
        post.delete()
        messages.success(request, "Post deleted.")
    return redirect('myPosts')


@login_required
def schedulePost(request, post_id):
    post = get_object_or_404(Post, id=post_id, user=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            updated = form.save()
            if updated.status == 'scheduled':
                schedule_post(updated)  # uses Celery or custom scheduling
            messages.success(request, "Post scheduled!")
            return redirect('creatorDashboard')
    else:
        form = PostForm(instance=post)
    return render(request, 'posts/schedule_post.html', {'form': form, 'post': post})


####################
# POST APPROVAL    #
####################

@login_required
def approvePosts(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')
    pending_posts = Post.objects.filter(status='scheduled')
    return render(request, 'posts/approvePosts.html', {'pending_posts': pending_posts})


@login_required
def approvePost(request, post_id):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    post = get_object_or_404(Post, id=post_id, status='scheduled')
    post.status = 'approved'
    post.save()
    messages.success(request, f"Post by {post.user.username} has been approved.")
    return redirect('approvePosts')


@login_required
def rejectPost(request, post_id):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    post = get_object_or_404(Post, id=post_id, status='scheduled')
    post.status = 'draft'
    post.save()
    messages.warning(request, f"Post by {post.user.username} has been sent back to draft.")
    return redirect('approvePosts')

@login_required
def approvePostAction(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.status = 'approved'
    post.save()
    # After approving:
    if post.status == 'approved':
        send_post_notification(
            user_email=post.user.email,
            subject="✅ Your post has been approved!",
            message=f"Hi {post.user.username},\n\nYour post titled \"{post.content[:50]}...\" has been approved and scheduled for {post.scheduled_time}.\n\n- DigiManager Team"
        )

    # In approvePostAction:
    send_notification(post.user, 'Post Approved', f'Your post "{post.content[:50]}" was approved.')

    return redirect('approvePosts')

@login_required
def rejectPostAction(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.status = 'rejected'
    post.save()
    return redirect('approvePosts')


#################
# PLATFORMS     #
#################

@login_required
def managePlatforms(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    platforms = Platform.objects.filter(added_by=request.user).order_by('-created_at')
    form = PlatformForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        platform = form.save(commit=False)
        platform.added_by = request.user
        platform.save()
        messages.success(request, f"{platform.name.title()} added successfully.")
        return redirect('managePlatforms')

    return render(request, 'platforms/managePlatforms.html', {
        'form': form,
        'platforms': platforms,
    })

@login_required
def editPlatform(request, pk):
    platform = get_object_or_404(Platform, pk=pk, added_by=request.user)
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    form = PlatformForm(request.POST or None, instance=platform)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Platform updated successfully.")
        return redirect('managePlatforms')

    return render(request, 'platforms/editPlatform.html', {'form': form, 'platform': platform})

@login_required
def deletePlatform(request, pk):
    platform = get_object_or_404(Platform, pk=pk, added_by=request.user)
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    if request.method == 'POST':
        platform.delete()
        messages.success(request, "Platform deleted successfully.")
        return redirect('managePlatforms')

    return render(request, 'platforms/deletePlatform.html', {'platform': platform})


##################
# DASHBOARDS     #
##################

User = get_user_model()

@login_required
def admDashboard(request):
    if request.user.role != 'admin':
        return redirect('unauthorized')
    users = User.objects.all()
    posts = Post.objects.all()
    return render(request, 'dashboards/admDashboard.html', {
        'users': users,
        'posts': posts,
    })

@login_required
def managerDashboard(request):
    if request.user.role != 'manager':
        return redirect('unauthorized')
    scheduled_posts = Post.objects.filter(status='scheduled', scheduled_time__lte=timezone.now())
    return render(request, 'dashboards/managerDashboard.html', {
        'scheduled_posts': scheduled_posts,
    })

@login_required
def creatorDashboard(request):
    if request.user.role != 'creator':
        return redirect('unauthorized')
    my_posts = Post.objects.filter(user=request.user).order_by('-created_at')[:3]
    platforms = Platform.objects.all()
    return render(request, 'dashboards/creatorDashboard.html', {
        'posts': my_posts,
        'platforms': platforms,
    })

def unauthorized(request):
    return render(request, 'dashboards/unauthorized.html')


##################
# DRAFTS VIEW    #
##################

@login_required
def drafts(request):
    user_drafts = Post.objects.filter(user=request.user, status='draft').order_by('-created_at')
    return render(request, 'scheduler/drafts.html', {'drafts': user_drafts})


##################
# ANALYTICS      #
##################

@login_required
def analyticsDashboard(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('unauthorized')

    # --- 1. Status Distribution ---
    status_counts = Post.objects.values('status').annotate(count=Count('status'))
    status_data = {item['status'].capitalize(): item['count'] for item in status_counts}

    # --- 2. Monthly Post Trends (Last 6 months) ---
    months = []
    post_counts = []
    now = timezone.now()

    for i in range(5, -1, -1):
        target_date = now - timedelta(days=30 * i)
        month_name = calendar.month_name[target_date.month]
        year = target_date.year
        month = target_date.month

        count = Post.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).count()

        months.append(month_name)
        post_counts.append(count)

    # --- 3. Platform Distribution ---
    platform_counts_raw = Post.objects.values('platform__name').annotate(count=Count('id'))
    platform_labels = []
    platform_counts = []

    for item in platform_counts_raw:
        platform_labels.append(item['platform__name'].title())
        platform_counts.append(item['count'])

    # --- 4. Platform Post Trends (Line Chart, over past 6 months) ---
    platform_trend_labels = months.copy()  # Use same month labels for all platforms
    platform_trend_data = defaultdict(list)
    platforms = Platform.objects.all().values_list('name', flat=True).distinct()

    for platform in platforms:
        for i in range(5, -1, -1):
            target_date = now - timedelta(days=30 * i)
            count = Post.objects.filter(
                platform__name=platform,
                created_at__year=target_date.year,
                created_at__month=target_date.month
            ).count()
            platform_trend_data[platform.title()].append(count)

    return render(request, 'dashboards/analytics.html', {
        # Status Chart
        'status_labels': list(status_data.keys()),
        'status_values': list(status_data.values()),

        # Monthly Chart
        'month_labels': months,
        'month_data': post_counts,

        # Platform Distribution Chart
        'platform_labels': platform_labels,
        'platform_counts': platform_counts,

        # Platform Trends (Line)
        'platform_trend_labels': platform_trend_labels,
        'platform_trend_data': dict(platform_trend_data),  # Convert defaultdict to regular dict
    })



#################
##NOTIFICATIONS##
#################
def send_notification(user, subject, message):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

################
##Excel Export##
################

@login_required
def exportPostsExcel(request):
    if request.user.role != 'admin':
        return redirect('unauthorized')

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Posts'

    headers = ['ID', 'User', 'Platform', 'Content', 'Status', 'Scheduled Time']
    sheet.append(headers)

    for post in Post.objects.all():
        sheet.append([
            post.id,
            post.user.username,
            post.platform.name,
            post.content[:50],
            post.status,
            post.scheduled_time.strftime("%Y-%m-%d %H:%M"),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename=posts_export.xlsx'
    workbook.save(response)
    return response


@login_required
def exportPostsPdf(request):
    if request.user.role != 'admin':
        return redirect('unauthorized')

    posts = Post.objects.all()
    template = get_template('exports/postsPdf.html')
    html = template.render({'posts': posts})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="posts_export.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("PDF generation error", status=500)

    return response

