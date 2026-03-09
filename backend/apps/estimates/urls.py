"""
URL configuration for estimates app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EstimateViewSet

app_name = "estimates"

router = DefaultRouter()
router.register(r"", EstimateViewSet, basename="estimate")

urlpatterns = [
    path("", include(router.urls)),
]
