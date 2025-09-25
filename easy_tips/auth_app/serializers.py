from rest_framework import serializers
from .models import UserData

class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserData
        fields = ['uuid', 'phone_number', 'name', 'email', 'avatar_url', 'goal', 'payment_goal', 'is_profile_complete']