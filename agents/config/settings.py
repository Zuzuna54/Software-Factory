import os
import dj_database_url  # Import dj-database-url

# Default DATABASE_URL if not set in environment (for local dev)
# Ensure it uses a standard scheme for parsing below
DEFAULT_DATABASE_URL = (
    "postgresql://agent_user:agent_password@localhost:5432/agent_team"
)
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

# Basic Django settings required by django-celery-beat
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-placeholder-key-for-celery-beat"
)

# Prepare URL for dj-database-url (replace asyncpg scheme if present)
django_db_url = DATABASE_URL
if django_db_url.startswith("postgresql+asyncpg://"):
    django_db_url = django_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

# Configure DATABASES using dj-database-url with the adjusted URL
DATABASES = {"default": dj_database_url.parse(django_db_url, conn_max_age=600)}

# Ensure the correct engine is used (should be inferred correctly now)
# If asyncpg is strictly required by other parts, you might need adjustments
# For django-celery-beat migrations, standard psycopg2 engine is usually fine.
# If DATABASE_URL uses 'postgresql+asyncpg', dj-database-url might need help.
# Override engine if necessary:
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

# Timezone settings (important for scheduling)
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_TZ = True

# Celery Beat specific settings (optional, defaults are usually fine)
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Minimal INSTALLED_APPS required by django-celery-beat
# We don't need full Django functionality, just what the beat scheduler uses
INSTALLED_APPS = (
    "django_celery_beat",
    # Add 'django.contrib.admin', 'django.contrib.auth', etc. if you plan to use the Django admin for beat schedules
)

# Suppress Django system check warnings about missing migrations for beat, etc.
# If you don't intend to run full Django `manage.py migrate`
SILENCED_SYSTEM_CHECKS = ["database.E001"]

# Default settings for USE_DEPRECATED_PYTZ (needed by timezone_field < 4.0)
# Django 4.0+ defaults USE_DEPRECATED_PYTZ to False. Django-celery-beat's
# dependency timezone_field might need this explicitly set for older Django compat.
# Set based on typical Django 3.x behavior if needed, otherwise omit.
# USE_DEPRECATED_PYTZ = False # Usually the default for modern Django

# --- DEBUGGING PRINT ---
import sys

print(f"DEBUG [settings.py]: DATABASES = {DATABASES}", file=sys.stderr)
# --- END DEBUGGING PRINT ---
