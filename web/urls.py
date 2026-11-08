from django.urls import path

from . import views

urlpatterns = [
    path("state/", views.api_state, name="api_state"),
    path("stream/", views.api_stream, name="api_stream"),
    path("outputs/", views.api_outputs, name="api_outputs"),
    path("outputs/off/", views.api_outputs_off, name="api_outputs_off"),
    path("alert/ack/", views.api_alert_ack, name="api_alert_ack"),
    path("sim/<str:action>/", views.api_sim_action, name="api_sim_action"),
    path("logs/", views.api_logs, name="api_logs"),
    path("selftest/", views.api_selftest, name="api_selftest"),
]
