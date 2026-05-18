from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generateCaption, name='generateCaption'),
    path('caption/<int:pk>/', views.captionDetail, name='captionDetail'),
]