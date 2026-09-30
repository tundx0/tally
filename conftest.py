import pytest
from rest_framework.test import APIClient

from analytics.models import Project


@pytest.fixture
def project(db):
    return Project.objects.create(name="Test project")


@pytest.fixture
def api_client():
    return APIClient()
