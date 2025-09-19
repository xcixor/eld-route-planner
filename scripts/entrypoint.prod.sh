#!/bin/sh

# Source environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Apply database migrations
echo "Applying database migrations..."
# Start the Django application
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py create_admin
uv run python manage.py collectstatic --noinput
uv run gunicorn -b 0.0.0.0:8000 app.wsgi:application --timeout 90
exec "$@"