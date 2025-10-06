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

class OrganizationUserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserData
        fields = [
            'uuid',
            'name',
            'avatar_url',
            'description',
            'is_profile_complete',
            'balance'
        ]
        read_only_fields = ['uuid', 'is_profile_complete', 'balance']


class OrganizationRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = UserData
        fields = ['login', 'password', 'password_confirm']

    def validate_login(self, value):
        if UserData.objects.filter(login=value).exists():
            raise serializers.ValidationError("Login is already taken")
        if len(value) < 3:
            raise serializers.ValidationError("Login must contain at least 3 characters")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "The passwords don't match"})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        organization = UserData.objects.create(
            **validated_data,
            user_type='organization',
            is_profile_complete=False
        )
        organization.set_password(password)
        return organization


class OrganizationLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField()


class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserData
        fields = ['name', 'description']

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("The name must contain at least 2 characters.")
        return value

    def update(self, instance, validated_data):
        if not validated_data.get('avatar_url'):
            validated_data['avatar_url'] = generate_avatar_url()

        instance = super().update(instance, validated_data)

        has_name = bool(instance.name and instance.name.strip())
        has_description = bool(instance.description and instance.description.strip())

        instance.is_profile_complete = has_name and has_description
        instance.save(update_fields=['is_profile_complete'])

        return instance


class AddEmployeeSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    def validate_phone_number(self, value):
        pattern = r'^\+?\d{9,15}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Please enter a valid phone number (9 to 15 digits, including '+')."
            )

        # We check whether the number is already an employee of this organization.
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if UserData.objects.filter(
                    phone_number=value,
                    organization=request.user
            ).exists():
                raise serializers.ValidationError("This number has already been added as an employee.")

        return value
