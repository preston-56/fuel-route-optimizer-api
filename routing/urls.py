from django.urls import path
from .views import OptimalRouteView, HealthCheckView, RouteMapView

urlpatterns = [
    path('route/', OptimalRouteView.as_view(), name='optimal-route'),
    path('route/map/', RouteMapView.as_view(), name='route-map'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
