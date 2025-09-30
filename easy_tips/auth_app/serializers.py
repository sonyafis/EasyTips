from rest_framework import serializers
from .models import UserData
import re

from .utils import generate_avatar_url, generate_random_name


class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserData
        fields = [
            'uuid',
            'phone_number',
            'name',
            'email',
            'avatar_url',
            'goal',
            'payment_goal',
            'is_profile_complete',
            'balance'
        ]
        read_only_fields = ['uuid', 'is_profile_complete', 'balance']

    def validate_phone_number(self, value):
        pattern = r'^\+?\d{9,15}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Введите корректный номер телефона (от 9 до 15 цифр, можно с '+')."
            )
        return value

    def validate_name(self, value):
        if value:
            if len(value.strip()) < 2:
                raise serializers.ValidationError("The name must contain at least 2 characters.")
            if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', value):
                raise serializers.ValidationError(
                    "The name can only contain letters, spaces, or hyphens."
                )
        return value

    def validate_email(self, value):
        if value:
            if len(value) > 100:
                raise serializers.ValidationError("Email cannot be longer than 100 characters.")

            email_regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
            if not re.match(email_regex, value):
                raise serializers.ValidationError("Please enter a valid email address.")
        return value

    def update(self, instance, validated_data):
        if not validated_data.get("name"):
            validated_data["name"] = generate_random_name()

        instance = super().update(instance, validated_data)

        instance.is_profile_complete = instance.check_profile_complete()
        if not instance.avatar_url:
            instance.avatar_url = generate_avatar_url()
            instance.save(update_fields=["avatar_url"])

        return instance



