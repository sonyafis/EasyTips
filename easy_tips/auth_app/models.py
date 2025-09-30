import uuid
from django.db import models

class UserData(models.Model):
    USER_TYPES = [
        ('guest', 'Гость'),
        ('employee', 'Сотрудник'),
        ('organization', 'Организация'),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    goal = models.TextField(blank=True, null=True)
    payment_goal = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    user_type = models.CharField(
        max_length=20, choices=USER_TYPES, default='employee'
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_profile_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user_type}: {self.phone_number or 'Guest'} - {self.name}"

    def check_profile_complete(self):
        required_fields = []
        self.is_profile_complete = all(required_fields)
        self.save(update_fields=["is_profile_complete"])
        return self.is_profile_complete

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_username(self):
        return str(self.uuid)

class Session(models.Model):
    SESSION_TYPES = [
        ('guest', 'Гость'),
        ('employee', 'Сотрудник'),
        ('organization', 'Организация'),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_data = models.ForeignKey(UserData, on_delete=models.CASCADE)
    session_type = models.CharField(
        max_length=20, choices=SESSION_TYPES, default='employee'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.uuid} for {self.user_data.phone_number}"