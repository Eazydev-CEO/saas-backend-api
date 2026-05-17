from django.apps import AppConfig


class APIKeysConfig(AppConfig):
    name = "apps.api_keys"
    verbose_name = "API Keys"

    def ready(self) -> None:  # pragma: no cover
        # Register the OpenAPI extension for APIKeyAuthentication
        from . import schema  # noqa: F401
