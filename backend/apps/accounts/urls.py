"""
URL configuration for accounts app.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    BusinessProfileView,
    ChangePasswordView,
    CustomTokenObtainPairView,
    LogoutView,
    RegisterView,
    UserProfileView,
)

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # User profile
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    # Business profile
    path("business-profile/", BusinessProfileView.as_view(), name="business-profile"),
]
