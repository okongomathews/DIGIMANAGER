from django.urls import path
from . import views

urlpatterns = [
    path('security/', views.security_center, name='security_center'),
    path('accounts/', views.account_directory, name='account_directory'),
    path('accounts/<int:user_id>/update/', views.update_account, name='update_account'),
    path('profile/', views.profile_view, name='profile'),
]
