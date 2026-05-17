from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"
    verbose_name = "Users"

    def ready(self) -> None:  # pragma: no cover
        from . import signals  # noqa: F401
