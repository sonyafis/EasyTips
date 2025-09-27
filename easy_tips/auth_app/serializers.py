from rest_framework import serializers
from .models import UserData
import re

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

    def validate_payment_goal(self, value):
        if value and len(value) > 255:
            raise serializers.ValidationError(
                "The payment purpose cannot exceed 255 characters."
            )
        return value

    # def validate(self, attrs):
    #     name = attrs.get('name') or (self.instance.name if self.instance else None)
    #     email = attrs.get('email') or (self.instance.email if self.instance else None)

    #     if name and not email:
    #         raise serializers.ValidationError({
    #             'email': "If a name is specified, you must also indicate an email."
    #         })

    #     return attrs
