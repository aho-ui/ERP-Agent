from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        import threading
        def _setup():
            from django.core.management import call_command
            call_command("migrate", "--run-syncdb", verbosity=0)
            call_command("create_default_users", verbosity=0)
        t = threading.Thread(target=_setup)
        t.start()
        t.join()
