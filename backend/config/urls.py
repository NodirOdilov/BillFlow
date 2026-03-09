"""
URL configuration for InvoiceForge project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API routes
    path("api/auth/", include("apps.accounts.urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/clients/", include("apps.clients.urls")),
    path("api/invoices/", include("apps.invoices.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/estimates/", include("apps.estimates.urls")),
    path("api/reports/", include("apps.reports.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
