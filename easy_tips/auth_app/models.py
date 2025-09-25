import uuid
from django.db import models


class UserData(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    goal = models.TextField(blank=True, null=True)
    payment_goal = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_profile_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.phone_number} - {self.name}"

    def check_profile_complete(self):
        """Проверяет, заполнен ли профиль"""
        required_fields = [self.name, self.email]
        self.is_profile_complete = all(required_fields)
        self.save()
        return self.is_profile_complete

    # Добавьте эти методы для совместимости с DRF
    @property
    def is_authenticated(self):
        """Всегда возвращает True для аутентифицированных пользователей"""
        return True

    @property
    def is_anonymous(self):
        """Всегда возвращает False (не анонимный пользователь)"""
        return False

    def get_username(self):
        """Возвращает идентификатор пользователя"""
        return str(self.uuid)
UserData.add_to_class('balance', models.DecimalField(max_digits=10, decimal_places=2, default=0))

class Session(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_data = models.ForeignKey(UserData, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.uuid} for {self.user_data.phone_number}"