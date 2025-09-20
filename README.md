# ELD Route Planner API

Django REST API for Electronic Logging Device (ELD) route planning and driver management.

## 🚀 Live API

**Staging:** <https://eld-route-planner-staging-1018057487898.us-east1.run.app/>

## 📋 Quick Start

### Development

```bash
# Setup environment with uv
uv venv
source .venv/bin/activate
uv sync

# Or setup manually
# source .venv/bin/activate
# uv pip install -r requirements.txt

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Testing

```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test tests.test_auth
python manage.py test tests.test_drivers
```

### Docker

```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up
```

## 🔑 API Endpoints

- **Authentication:** `/api/auth/` (login, register, logout)
- **Drivers:** `/api/drivers/` (CRUD operations)
- **Vehicles:** `/api/vehicles/` (fleet management)
- **Trips:** `/api/trips/` (route planning)
- **ELD Logs:** `/api/eld-logs/` (compliance tracking)
- **Documentation:** `/redoc/` (API docs)

## 🛠 Tech Stack

- Django 5.2 + Django REST Framework
- Knox Authentication (24h token expiry)
- PostgreSQL (production) / SQLite (development)
- Docker + Google Cloud Run
- CircleCI for CI/CD
