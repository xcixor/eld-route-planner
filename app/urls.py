"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="ELD Route Planner API",
        default_version='v1',
        description="""
        **Electronic Logging Device (ELD) Route Planning API**

        A comprehensive API for commercial vehicle route planning and ELD compliance management.

        ## Features:
        - **Trip Planning**: Plan routes with pickup/dropoff locations
        - **ELD Logging**: Generate compliant electronic log sheets
        - **HOS Compliance**: Hours of Service monitoring and validation
        - **Fleet Management**: Driver, vehicle, and load management
        - **Route Optimization**: Waypoints, fuel stops, and rest breaks

        ## Authentication:
        This API uses Token-based authentication. Include your token in the Authorization header:
        ```
        Authorization: Token <your_token_here>
        ```

        ## Main Endpoint:
        **POST /api/plan-trip/** - Core functionality that takes trip inputs and returns route + ELD logs
        """,
        terms_of_service="",
        contact=openapi.Contact(email=""),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    # Root URL redirect to API documentation
    path('', RedirectView.as_view(url='/redoc/', permanent=False), name='root-redirect'),

    path('admin/', admin.site.urls),

    # API Documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api-docs'),

    # Main API
    path('api/', include('eld_system.urls')),
]

# Add debug toolbar in development
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    ]
