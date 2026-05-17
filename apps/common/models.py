"""Reusable abstract model bases."""
from __future__ import annotations

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract model with a UUID4 primary key. Use for all user-facing entities."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract model providing `created_at` and `updated_at` timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """Convenience base for entities that need both UUID PK and timestamps."""

    class Meta:
        abstract = True
