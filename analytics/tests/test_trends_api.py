from datetime import UTC, datetime

from django.urls import reverse

from analytics.models import Event


def trends_url(project_id):
    return reverse("trends", kwargs={"project_id": project_id})


# Happy Path
def test_members_get_daily_counts_as_json(member_client, project):
    Event.objects.create(
        project=project,
        event="signed_up",
        distinct_id="user_1",
        properties={"plan": "pro"},
        timestamp=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    )
    params = {
        "event": "signed_up",
        "date_from": "2026-09-01",
        "date_to": "2026-09-03",
        "breakdown": "plan",
    }

    response = member_client.get(trends_url(project.id), params)

    assert response.status_code == 200
    assert response.json() == {
        "event": "signed_up",
        "date_from": "2026-09-01",
        "date_to": "2026-09-03",
        "breakdown": "plan",
        "math": "total",
        "series": [
            {
                "breakdown_value": "pro",
                "data": [
                    {"day": "2026-09-01", "count": 0},
                    {"day": "2026-09-02", "count": 1},
                    {"day": "2026-09-03", "count": 0},
                ],
            }
        ],
    }


def test_anonymous_user_is_rejected(api_client, project):
    response = api_client.get(trends_url(project.id), {"event": "signed_up"})

    assert response.status_code == 403


def test_non_member_gets_404(api_client, project, user):
    api_client.force_login(user)

    response = api_client.get(trends_url(project.id), {"event": "signed_up"})

    assert response.status_code == 404


def test_unknown_project_gets_404(member_client):
    response = member_client.get(trends_url(999_999), {"event": "signed_up"})

    assert response.status_code == 404


def test_invalid_params_return_400(member_client, project):
    response = member_client.get(trends_url(project.id))

    assert response.status_code == 400
    assert "event" in response.json()


def test_non_member_with_invalid_params_still_gets_404(api_client, project, user):
    api_client.force_login(user)

    response = api_client.get(trends_url(project.id))

    assert response.status_code == 404


def test_post_is_not_allowed(member_client, project):
    response = member_client.post(trends_url(project.id))

    assert response.status_code == 405
