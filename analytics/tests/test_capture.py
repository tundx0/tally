from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from analytics.models import Event, Project


def make_event(**overrides):
    event = {
        "event": "sign_up",
        "distinct_id": "user_1",
        "timestamp": "2026-05-10T00:00:21Z",
        "properties": {"plan": "pro"},
    }
    event.update(overrides)
    return event


def test_capture_valid_batch(api_client, project):
    payload = {
        "api_key": project.api_key,
        "batch": [make_event(), make_event(distinct_id="user_2")],
    }
    response = api_client.post(reverse("capture"), payload, format="json")
    assert response.status_code == 200
    assert response.json() == {"accepted": 2}
    assert Event.objects.filter(project=project).count() == 2


def test_capture_missing_timestamp_defaults_to_now(api_client, project):
    event = make_event()
    event.pop("timestamp")

    payload = {
        "api_key": project.api_key,
        "batch": [event],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 200
    saved = Event.objects.get(project=project)
    assert abs(saved.timestamp - timezone.now()) < timedelta(seconds=5)


def test_capture_missing_properties_defaults_to_empty_dict(api_client, project):
    event = make_event()
    event.pop("properties")

    payload = {
        "api_key": project.api_key,
        "batch": [event],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 200
    saved = Event.objects.get(project=project)
    assert saved.properties == {}


def test_capture_unknown_api_key_is_rejected(api_client, project):
    payload = {
        "api_key": "phc_does_not_exist",
        "batch": [make_event()],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 401
    assert Event.objects.count() == 0


def test_capture_missing_api_key_is_rejected(api_client, project):
    payload = {
        "batch": [make_event()],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 401
    assert Event.objects.count() == 0


def test_capture_one_bad_event_rejects_whole_batch(api_client, project):
    bad_event = make_event()
    bad_event.pop("event")

    payload = {
        "api_key": project.api_key,
        "batch": [make_event(), bad_event],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 400
    assert Event.objects.count() == 0


def test_capture_empty_batch_is_rejected(api_client, project):
    payload = {
        "api_key": project.api_key,
        "batch": [],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 400


def test_capture_batch_over_1000_events_is_rejected(api_client, project):
    payload = {
        "api_key": project.api_key,
        "batch": [make_event() for _ in range(1001)],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 400
    assert Event.objects.count() == 0


def test_capture_properties_must_be_an_object(api_client, project):
    payload = {
        "api_key": project.api_key,
        "batch": [make_event(properties=["plan", "pro"])],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 400
    assert Event.objects.count() == 0


def test_capture_body_that_is_a_list_does_not_crash(api_client, project):
    payload = {
        "api_key": project.api_key,
        "batch": [make_event()],
    }

    response = api_client.post(reverse("capture"), [payload], format="json")

    assert response.status_code in (400, 401)
    assert Event.objects.count() == 0


def test_capture_stores_events_only_in_the_key_owners_project(api_client, project):
    other_project = Project.objects.create(name="Other project")
    payload = {
        "api_key": project.api_key,
        "batch": [make_event()],
    }

    response = api_client.post(reverse("capture"), payload, format="json")

    assert response.status_code == 200
    assert project.events.count() == 1
    assert other_project.events.count() == 0


def test_capture_rejects_get(api_client, project):
    response = api_client.get(reverse("capture"))

    assert response.status_code == 405
