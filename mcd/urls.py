from django.urls import path

from . import views

app_name = "mcd"

urlpatterns = [
    path("", views.index, name="index"),
    path("devices/", views.page_devices, name="devices"),
    path("simulator/", views.page_simulator, name="simulator"),
    path("tests/", views.page_tests, name="tests"),
    path("stats/", views.page_stats, name="stats"),
    path("logs/", views.page_logs, name="logs"),
    path("diagnostics/", views.page_diagnostics, name="diagnostics"),
    path("operator/", views.page_operator, name="operator"),
    path("api/pins/", views.api_pins, name="api_pins"),
    path("api/accel/", views.api_accel, name="api_accel"),
    path("api/dashboard/", views.api_dashboard, name="api_dashboard"),
    path("api/selftest/", views.api_selftest, name="api_selftest"),
]
