#!/bin/sh
echo "Applying database migrations..."
# Start the Django application
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py create_admin
sh /home/app/load_fixtures.sh
uv run python manage.py collectstatic --noinput
uv run gunicorn -b 0.0.0.0:8000 app.wsgi:application --timeout 90
exec "$@"