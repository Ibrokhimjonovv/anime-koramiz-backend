from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from add_all.models import Notification
from users.models import PasswordResetToken, User


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="oldpass123"
        )

    @patch("django.core.mail.EmailMultiAlternatives.send", return_value=True)
    def test_password_reset_request_success(self, mock_send):
        response = self.client.post(
            reverse("password_reset_request"), {"email": self.user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("yuborildi", response.json()["message"])
        self.assertTrue(mock_send.called)

    def test_password_reset_request_not_found(self):
        response = self.client.post(
            reverse("password_reset_request"), {"email": "no@example.com"}
        )
        self.assertEqual(response.status_code, 404)

    def test_password_reset_verify_success(self):
        token = PasswordResetToken.objects.create(
            user=self.user,
            token="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        response = self.client.post(
            reverse("password_reset_verify"),
            {"email": self.user.email, "token": "123456"},
        )
        self.assertEqual(response.status_code, 200)

    def test_password_reset_verify_invalid(self):
        response = self.client.post(
            reverse("password_reset_verify"),
            {"email": self.user.email, "token": "wrong"},
        )
        self.assertEqual(response.status_code, 400)

    def test_password_reset_confirm_success(self):
        PasswordResetToken.objects.create(
            user=self.user,
            token="654321",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        response = self.client.post(
            reverse("password_reset_confirm"),
            {
                "email": self.user.email,
                "token": "654321",
                "new_password": "newpass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123"))

    def test_password_reset_confirm_invalid(self):
        response = self.client.post(
            reverse("password_reset_confirm"),
            {
                "email": self.user.email,
                "token": "wrong",
                "new_password": "x",
            },
        )
        self.assertEqual(response.status_code, 400)


class NotificationTests(TestCase):
    def setUp(self):
        self.notification = Notification.objects.create(title="Hello", text="World")

    def test_list_notifications(self):
        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)

    def test_detail_notification(self):
        response = self.client.get(
            reverse("notification-detail", kwargs={"pk": self.notification.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_read_notification(self):
        response = self.client.post(
            reverse("notification-read", kwargs={"pk": self.notification.pk})
        )
        self.assertIn(response.status_code, (200, 204))

    def test_view_notification(self):
        response = self.client.post(
            reverse("notification-view", kwargs={"pk": self.notification.pk})
        )
        self.assertIn(response.status_code, (200, 204))

    def test_unread_count(self):
        response = self.client.get(reverse("unread-notification-count"))
        self.assertEqual(response.status_code, 200)
