from django.urls import include, path

urlpatterns = [
    path("", include("mcd.urls")),
    path("api/", include("web.urls")),
]
