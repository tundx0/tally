from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication, exceptions

from .models import Project


class ProjectApiKeyAuthentication(authentication.BaseAuthentication):
    """Identifies the project sending events from the api_key in the request body."""

    def authenticate(self, request):
        if request.method != "POST":
            return None

        data = request.data
        api_key = data.get("api_key") if isinstance(data, dict) else None
        if not isinstance(api_key, str) or not api_key:
            raise exceptions.AuthenticationFailed("Missing api_key.")

        project = Project.objects.filter(api_key=api_key).first()
        if not project:
            raise exceptions.AuthenticationFailed("Invalid api_key.")

        return (AnonymousUser(), project)

    def authenticate_header(self, request):
        return 'ApiKey realm="api"'
