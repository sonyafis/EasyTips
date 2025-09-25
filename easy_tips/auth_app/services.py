import random
import hashlib
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import UserData, Session


class AuthService:
    @staticmethod
    def generate_verification_code():
        return str(random.randint(1000, 9999))

    @staticmethod
    def _hash_code(code: str) -> str:
        """Возвращает SHA256-хэш кода (строка в hex)."""
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def send_verification_code(phone_number: str) -> bool:
        code = AuthService.generate_verification_code()

        # ✅ Храним только хэш, не сам код
        code_hash = AuthService._hash_code(code)
        cache.set(f"verification_code_{phone_number}", code_hash, 300)

        # ⚠️ Отправляем только ПОЛНЫЙ код пользователю (не хэш!)
        # Здесь интеграция с SMS-сервисом (или пока print для теста)
        print(f"Код для {phone_number}: {code}")
        return True

    @staticmethod
    def verify_code(phone_number: str, code: str) -> bool:
        stored_hash = cache.get(f"verification_code_{phone_number}")
        if not stored_hash:
            return False
        # ✅ Сравниваем хэш введённого кода с хэшем из кеша
        return stored_hash == AuthService._hash_code(code)

    @staticmethod
    def get_or_create_user(phone_number):
        try:
            user_data = UserData.objects.get(phone_number=phone_number)
            created = False
            print(f"👤 Пользователь найден: {user_data.phone_number}")
        except UserData.DoesNotExist:
            user_data = UserData.objects.create(
                phone_number=phone_number,
                is_profile_complete=False  # Новый пользователь без профиля
            )
            created = True
            print(f"👤 Создан новый пользователь: {user_data.phone_number}")

        return user_data, created

    @staticmethod
    def create_session(user_data):
        expires_at = timezone.now() + timedelta(days=30)
        return Session.objects.create(user_data=user_data, expires_at=expires_at)
