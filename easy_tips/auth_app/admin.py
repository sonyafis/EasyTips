from django.contrib import admin
from .models import UserData, Session

@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'name', 'email', 'created_at', 'updated_at')
    search_fields = ('phone_number', 'name', 'email')
    readonly_fields = ('uuid', 'created_at', 'updated_at')

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user_data', 'is_active', 'created_at', 'expires_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('user_data__phone_number',)
    readonly_fields = ('uuid', 'created_at')
