"""Custom User model: email-keyed, UUID PK, role-aware."""
from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel

from .managers import UserManager


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    STAFF = "staff", "Staff"
    CUSTOMER = "customer", "Customer"


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """SaaS user.

    - UUID primary key (inherited from BaseModel).
    - Email is the unique identifier.
    - `role` drives RBAC permission classes.
    - `is_verified` gates access to verified-only endpoints.
    """

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    role = models.CharField(
        max_length=16, choices=UserRole.choices, default=UserRole.CUSTOMER, db_index=True
    )
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def mark_logged_in(self) -> None:
        """Update last_login_at; call from authentication services."""
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])
