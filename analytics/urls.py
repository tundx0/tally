from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    # Day 2: register your capture endpoint and viewsets here.
]
