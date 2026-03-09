"""
URL configuration for clients app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClientContactViewSet, ClientNoteViewSet, ClientViewSet

app_name = "clients"

router = DefaultRouter()
router.register(r"", ClientViewSet, basename="client")

# Nested routes for contacts and notes
contact_router = DefaultRouter()
contact_router.register(r"contacts", ClientContactViewSet, basename="client-contact")

note_router = DefaultRouter()
note_router.register(r"notes", ClientNoteViewSet, basename="client-note")

urlpatterns = [
    path(
        "<uuid:client_pk>/",
        include(contact_router.urls),
    ),
    path(
        "<uuid:client_pk>/",
        include(note_router.urls),
    ),
    path("", include(router.urls)),
]
