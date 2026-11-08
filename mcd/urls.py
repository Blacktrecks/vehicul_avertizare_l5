from django.urls import path

from . import views

app_name = "mcd"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/pins/", views.api_pins, name="api_pins"),
    path("api/accel/", views.api_accel, name="api_accel"),
    path("api/dashboard/", views.api_dashboard, name="api_dashboard"),
    path("api/selftest/", views.api_selftest, name="api_selftest"),
]
