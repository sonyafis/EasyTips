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

    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='employee')

    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_profile_complete = models.BooleanField(default=False)

    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)

    login = models.CharField(max_length=50, unique=True, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    organization = models.ForeignKey('self', on_delete=models.CASCADE,
                                   null=True, blank=True,
                                   related_name='employees')

    def __str__(self):
        return f"{self.user_type}: {self.phone_number or 'Guest'} - {self.name}"

    def check_profile_complete(self):

        required_fields = []
        self.is_profile_complete = all(required_fields)
        self.save(update_fields=["is_profile_complete"])
        return self.is_profile_complete

        if self.user_type == 'organization':
            required_fields = ['name', 'description']
            self.is_profile_complete = all(getattr(self, field) for field in required_fields)
        else:
            required_fields = []
            self.is_profile_complete = all(getattr(self, field) for field in required_fields)

        self.save(update_fields=["is_profile_complete"])
        return self.is_profile_complete

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
        self.save(update_fields=["password"])

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

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

    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='employee')

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.uuid} for {self.user_data.phone_number}"