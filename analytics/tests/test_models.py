from datetime import UTC, datetime

import pytest
from django.db import IntegrityError

from analytics.models import Event, Person, Project


def test_project_gets_a_unique_api_key(db):
    a = Project.objects.create(name="A")
    b = Project.objects.create(name="B")

    assert a.api_key.startswith("phc_")
    assert a.api_key != b.api_key


def test_distinct_id_is_unique_per_project(project):
    Person.objects.create(project=project, distinct_id="user-1")

    with pytest.raises(IntegrityError):
        Person.objects.create(project=project, distinct_id="user-1")


def test_same_distinct_id_allowed_in_another_project(project):
    other = Project.objects.create(name="Other")
    Person.objects.create(project=project, distinct_id="user-1")

    Person.objects.create(project=other, distinct_id="user-1")


def test_can_filter_events_by_json_property(project):
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    Event.objects.create(
        project=project,
        event="signed_up",
        distinct_id="a",
        timestamp=ts,
        properties={"plan": "pro"},
    )
    Event.objects.create(
        project=project,
        event="signed_up",
        distinct_id="b",
        timestamp=ts,
        properties={"plan": "free"},
    )

    pro = Event.objects.filter(project=project, properties__plan="pro")

    assert [e.distinct_id for e in pro] == ["a"]
