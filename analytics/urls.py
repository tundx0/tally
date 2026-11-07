from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("capture/", views.CaptureView.as_view(), name="capture"),
    path("projects/<int:project_id>/trends/", views.TrendsView.as_view(), name="trends"),
]
