"""Plan-aware throttling.

Each request scopes to the user's current plan slug. Rates are defined in
`REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` as `plan_free`, `plan_pro`,
`plan_enterprise`, etc.
"""
from __future__ import annotations

from typing import Any

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle


class PlanScopedUserThrottle(SimpleRateThrottle):
    """Rate-limit authenticated users by their subscription plan.

    Unauthenticated users fall through to other throttles (e.g. AnonRateThrottle).
    """

    cache_format = "throttle_%(scope)s_%(ident)s"
    scope = "plan_free"  # placeholder; overwritten per-request

    def get_cache_key(self, request: Request, view: Any) -> str | None:
        if not request.user or not request.user.is_authenticated:
            return None

        plan_slug = self._user_plan_slug(request)
        self.scope = f"plan_{plan_slug}"
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}

    @staticmethod
    def _user_plan_slug(request: Request) -> str:
        """Resolve the user's plan slug. Falls back to 'free'."""
        # Set by SubscriptionContextMiddleware
        plan_slug = getattr(request, "subscription_plan_slug", None)
        return plan_slug or "free"
