from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("capture/", views.CaptureView.as_view(), name="capture"),
]
