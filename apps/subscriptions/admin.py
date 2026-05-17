"""Subscription admin."""
from __future__ import annotations

from django.contrib import admin

from .models import Plan, Subscription, UsageQuota


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price", "request_quota", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "started_at", "expires_at", "auto_renew")
    list_filter = ("status", "plan", "auto_renew")
    search_fields = ("user__email",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("user", "plan")


@admin.register(UsageQuota)
class UsageQuotaAdmin(admin.ModelAdmin):
    list_display = ("subscription", "period_start", "period_end", "requests_used")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("subscription",)
