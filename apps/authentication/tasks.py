"""Background email tasks.

Both tasks are idempotent and retry on transient SMTP errors.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
User = get_user_model()


def _send_html_email(*, subject: str, to: str, template: str, context: dict) -> None:
    text_body = render_to_string(f"emails/{template}.txt", context)
    html_body = render_to_string(f"emails/{template}.html", context)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    name="authentication.send_verification_email",
)
def send_verification_email(self, *, user_id: str, token: str) -> None:
    """Send the email verification message."""
    user = User.objects.filter(id=user_id).first()
    if not user:
        logger.warning("send_verification_email: user %s not found", user_id)
        return
    verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
    _send_html_email(
        subject="Verify your email address",
        to=user.email,
        template="verification",
        context={
            "user": user,
            "verify_url": verify_url,
            "ttl_hours": settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS,
        },
    )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    name="authentication.send_password_reset_email",
)
def send_password_reset_email(self, *, user_id: str, token: str) -> None:
    """Send the password reset message."""
    user = User.objects.filter(id=user_id).first()
    if not user:
        logger.warning("send_password_reset_email: user %s not found", user_id)
        return
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    _send_html_email(
        subject="Reset your password",
        to=user.email,
        template="password_reset",
        context={
            "user": user,
            "reset_url": reset_url,
            "ttl_hours": settings.PASSWORD_RESET_TOKEN_TTL_HOURS,
        },
    )
