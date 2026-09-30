import secrets

from django.conf import settings
from django.db import models


def generate_api_key() -> str:
    return f"phc_{secrets.token_urlsafe(24)}"


class Project(models.Model):
    """A tenant. Every Person and Event belongs to exactly one project, and
    every query must be scoped by it."""

    name = models.CharField(max_length=200)
    # Public key embedded in client SDKs to send events (like PostHog's phc_ keys).
    api_key = models.CharField(max_length=64, unique=True, default=generate_api_key)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="projects")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Person(models.Model):
    """Someone who performed events, identified by the app's own user id."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="persons")
    distinct_id = models.CharField(max_length=200)
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "distinct_id"], name="unique_person_per_project"
            ),
        ]

    def __str__(self) -> str:
        return self.distinct_id


class Event(models.Model):
    """One thing that happened, e.g. "$pageview" or "signed_up".

    distinct_id is stored as a plain string rather than a ForeignKey to Person:
    ingestion must never block on a person lookup, and the table will be huge.
    """

    # No standalone index: the composite indexes below already start with project.
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="events", db_index=False
    )
    event = models.CharField(max_length=200)
    distinct_id = models.CharField(max_length=200)
    properties = models.JSONField(default=dict, blank=True)
    # When it happened on the client, vs. when we stored it.
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # Serves "events of type X in project P over a time range" (trends).
            models.Index(fields=["project", "event", "timestamp"]),
            # Serves "a person's activity timeline".
            models.Index(fields=["project", "distinct_id", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.event} by {self.distinct_id}"
