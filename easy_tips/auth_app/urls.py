from django.urls import path
from . import views

urlpatterns = [
    path('send-code/', views.send_code, name='send_code'),
    path('verify-code/', views.verify_code, name='verify_code'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('profile-status/', views.profile_status, name='profile_status'),
    path('guest-login/', views.guest_login),
    # path('organization-register/', views.organization_register),
    path('logout/', views.logout, name='logout'),
    path('renew-auth/', views.renew_auth, name='renew_auth'),
    path('logout/', views.logout, name='logout'),
    path('renew-auth/', views.renew_auth, name='renew_auth'),
    path('organization/register/', views.organization_register, name='organization_register'),
    path('organization/login/', views.organization_login, name='organization_login'),
    path('organization/complete-profile/', views.organization_complete_profile, name='organization_complete_profile'),
    path('organization/profile/', views.organization_profile, name='organization_profile'),
    path('organization/add-employee/', views.add_employee, name='add_employee'),
    path('organization/employees/', views.organization_employees, name='organization_employees'),
]