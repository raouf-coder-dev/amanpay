from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Ensure the post_save Wallet-creation signal is registered.
        # The receiver lives in accounts/models.py; importing models forces it to load.
        from . import models  # noqa: F401
