import secrets
import string
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.CharField(max_length=512)
    password = models.CharField(max_length=32)
    profile_image = models.ImageField(
        upload_to="profile_images/", null=True, blank=True
    )
    # Bu fieldlarni qo'shing
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.username


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = "".join(secrets.choice(string.digits) for _ in range(6))

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)

        super().save(*args, **kwargs)