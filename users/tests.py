from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import PasswordResetToken, User


class UserModelTests(TestCase):
    def test_str_returns_username(self):
        user = User.objects.create(
            username="john", email="john@example.com", password="testpass123"
        )
        self.assertEqual(str(user), "john")


class PasswordResetTokenTests(TestCase):
    def test_token_and_expiry_auto_generated_on_save(self):
        user = User.objects.create(
            username="alice", email="alice@example.com", password="pass123"
        )
        token = PasswordResetToken.objects.create(user=user)

        self.assertTrue(token.token.isdigit())
        self.assertEqual(len(token.token), 6)

        self.assertAlmostEqual(
            token.expires_at,
            timezone.now() + timedelta(minutes=30),
            delta=timedelta(seconds=2),
        )

    def test_custom_token_and_expiry_preserved(self):
        user = User.objects.create(
            username="bob", email="bob@example.com", password="pass123"
        )
        custom_expiry = timezone.now() + timedelta(hours=1)
        token = PasswordResetToken.objects.create(
            user=user, token="123456", expires_at=custom_expiry
        )

        self.assertEqual(token.token, "123456")
        self.assertEqual(token.expires_at, custom_expiry)
