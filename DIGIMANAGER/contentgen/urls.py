from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generateCaption, name='contentgen_generateCaption'),
    path('caption/<int:pk>/', views.captionDetail, name='contentgen_captionDetail'),
]
