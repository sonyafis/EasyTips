from django.urls import path
from . import views

urlpatterns = [
    path('send-code/', views.send_code, name='send_code'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('profile-status/', views.profile_status, name='profile_status'),
    path('logout/', views.logout, name='logout'),
]