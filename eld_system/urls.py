from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'drivers', views.DriverViewSet)
router.register(r'vehicles', views.VehicleViewSet)
router.register(r'shippers', views.ShipperViewSet)
router.register(r'loads', views.LoadViewSet)
router.register(r'trips', views.TripViewSet)
router.register(r'eld-logs', views.ELDLogSheetViewSet, basename='eldlogsheet')
router.register(r'duty-periods', views.DutyStatusPeriodViewSet)
router.register(r'hos-cycles', views.HOSCycleTrackingViewSet)

urlpatterns = [
    path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/auth/logout-all/', views.LogoutAllView.as_view(), name='logout-all'),
    path('api/auth/register/', views.RegisterView.as_view(), name='register'),
    path('api/', include(router.urls)),
    path('api/plan-trip/', views.TripPlanningView.as_view(), name='plan-trip'),
]