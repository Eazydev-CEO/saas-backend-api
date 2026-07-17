"""Subscription endpoints."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import NotFound
from apps.common.responses import success

from . import services
from .models import Plan
from .selectors import get_active_subscription
from .serializers import PlanSerializer, SubscribeSerializer, SubscriptionSerializer


class PlanListView(APIView):
    """Public list of subscribable plans."""

    permission_classes: list = []
    authentication_classes: list = []

    @extend_schema(
        responses=PlanSerializer(many=True),
        tags=["Subscriptions"],
        summary="List available plans",
    )
    def get(self, request: Request) -> Response:
        plans = Plan.objects.filter(is_active=True).order_by("price")
        return success(PlanSerializer(plans, many=True).data)


class MySubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=SubscriptionSerializer,
        tags=["Subscriptions"],
        summary="Get my current subscription",
    )
    def get(self, request: Request) -> Response:
        sub = get_active_subscription(request.user)
        if not sub:
            raise NotFound("No active subscription.", code="no_active_subscription")
        return success(SubscriptionSerializer(sub).data)


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SubscribeSerializer,
        responses=SubscriptionSerializer,
        tags=["Subscriptions"],
        summary="Subscribe / upgrade / downgrade to a plan",
    )
    def post(self, request: Request) -> Response:
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = services.subscribe(
            user=request.user,
            plan_slug=serializer.validated_data["plan_slug"],
        )
        return success(SubscriptionSerializer(sub).data, "Subscription updated.")


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=SubscriptionSerializer,
        tags=["Subscriptions"],
        summary="Cancel active subscription (downgrades to Free)",
    )
    def post(self, request: Request) -> Response:
        sub = services.cancel(user=request.user)
        return success(SubscriptionSerializer(sub).data, "Subscription canceled.")
