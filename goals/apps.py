from django.apps import AppConfig


class GoalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'goals'
    verbose_name = 'Metas Financeiras'

    def ready(self):
        from . import signals  # noqa: F401
