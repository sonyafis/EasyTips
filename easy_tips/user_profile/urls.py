from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('tips/get-qr/', views.get_qr_code, name='get_qr_code'),
    path('tips/payment/', views.payment_tips, name='payment_tips'),
    path('tips/withdraw/', views.withdraw_tips, name='withdraw_tips'),
    path('tips/balance/', views.get_balance, name='get_balance'),
    path('tips/history/', views.transaction_history, name='transaction_history'),
]