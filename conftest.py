import pytest
from rest_framework.test import APIClient

from accounts.models import User
from analytics.models import Project


@pytest.fixture
def project(db):
    return Project.objects.create(name="Test project")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ola")


@pytest.fixture
def member_client(api_client, project, user):
    project.members.add(user)
    api_client.force_login(user)
    return api_client
