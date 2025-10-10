from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('employee/qr-code/', views.get_employee_qr_code, name='get_employee_qr_code'),
    path('guest-tip/payment/', views.create_guest_tip_payment, name='create_guest_tip_payment'),
    path('employee/<uuid:employee_uuid>/info/', views.get_employee_info, name='get_employee_info'),
    path('tips/withdraw/', views.withdraw_tips, name='withdraw_tips'),
    path('tips/balance/', views.get_balance, name='get_balance'),
    path('tips/history/', views.transaction_history, name='transaction_history'),
    path('tips/statistics/', views.transaction_statistics, name='transaction_statistics'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
]