# notifications/apps.py
from django.apps import AppConfig
import sys
import os # Import os for a more robust check

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    # ready method MUST BE INDENTED to be part of this class
    def ready(self):
        # This check helps ensure the scheduler starts only once in the main process
        # during development with the autoreloader or when running daphne directly.
        # Check if 'manage.py' is in the command line arguments for 'runserver'
        is_runserver_command = any('manage.py' in arg and 'runserver' in arg for arg in sys.argv) or 'runserver' in sys.argv
        is_daphne_command = 'daphne' in sys.argv[0].lower() # Check if daphne is the command, case-insensitive for safety

        # Start scheduler if:
        # 1. RUN_MAIN is true (main runserver process, not reloader child) AND it's a runserver command
        # 2. It's a direct daphne call (and not a reloader child process of runserver if daphne is somehow invoked by it)
        should_start_scheduler = (os.environ.get('RUN_MAIN') == 'true' and is_runserver_command) or \
                                 (is_daphne_command and not os.environ.get('RUN_MAIN'))

        if should_start_scheduler:
            try:
                from . import scheduler
                print("Starting notifications scheduler...")
                scheduler.start() # Call the start function from your scheduler.py
            except ImportError:
                print("Could not import or start scheduler in notifications/apps.py. "
                      "This might be expected during initial migrations if models are not ready, "
                      "or there could be an import error in scheduler.py.")
            except Exception as e:
                print(f"An unexpected error occurred while starting the scheduler: {e}")