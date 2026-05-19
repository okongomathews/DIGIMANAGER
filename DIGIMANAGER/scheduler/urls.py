from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    # AI Image
    path('ai/generate/<int:post_id>/', views.generate_ai_image, name='generate_ai_image'),
    path('ai/generate/', views.generate_ai_image, name='generate_ai_image'),
    path('ai/refine/', views.refine_ai_image, name='refine_ai_image'),
    path('ai/sd/', views.generate_image_sd, name='generate_sd_image'),
    path('generate-ai-image/', views.generate_ai_image, name='generate_ai_image'),  # for new post
    path('generate-ai-image/<int:post_id>/', views.generate_ai_image, name='generate_ai_image_with_id'),  # for edit


    # Caption
    path('caption/generate/', views.generateCaption, name='generateCaption'),
    path('caption/history/', views.captionHistory, name='captionHistory'),

    # Posts & drafts
    path('posts/create/', views.createPost, name='createPost'),
    path('posts/', views.myPosts, name='myPosts'),
    path('posts/drafts/', views.drafts, name='drafts'),
    path('posts/view/<int:post_id>/', views.viewPost, name='viewPost'),
    path('post/<int:post_id>/edit/', views.editPost, name='editPost'),
    path('posts/delete/<int:post_id>/', views.deletePost, name='deletePost'),
    path('posts/<int:post_id>/schedule/', views.schedulePost, name='schedulePost'),


    # Approvals
    path('posts/approve/', views.approvePosts, name='approvePosts'),
    path('posts/approve/<int:post_id>/', views.approvePost, name='approvePost'),
    path('posts/approve/action/', views.approvePostAction, name='approvePostAction'),
    path('posts/reject/', views.rejectPostAction, name='rejectPostAction'),
    path('posts/reject/<int:post_id>/', views.rejectPost, name='rejectPost'),


    # Platforms
    path('platforms/manage/', views.managePlatforms, name='managePlatforms'),
    path('platforms/<int:post_id>/edit/', views.editPlatform, name='editPlatform'),
    path('platforms/<int:post_id>/delete/', views.deletePlatform, name='deletePlatform'),

    # Dashboards
    path('creator-dashboard/', views.creatorDashboard, name='creatorDashboard'),
    path('admin-dashboard/', views.admDashboard, name='admDashboard'),
    path('manager-dashboard/', views.managerDashboard, name='managerDashboard'),
    path('analytics/', views.analyticsDashboard, name='analyticsDashboard'),
    path('unauthorized/', views.unauthorized, name='unauthorized'),


    # Exports
    path('export/excel/', views.exportPostsExcel, name='export_posts_excel'),
    path('export/pdf/', views.exportPostsPdf, name='export_posts_pdf'),

]