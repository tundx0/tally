from datetime import UTC, date, datetime, timedelta

import pytest

from analytics.models import Event, Project
from analytics.trends import trends


def add_event(project, when, event="signed_up", distinct_id="user1", **properties):
    Event.objects.create(
        project=project, timestamp=when, event=event, distinct_id=distinct_id, properties=properties
    )


def counts(series):
    return [point["count"] for point in series["data"]]


def test_trends_counts_per_day_and_fills_missing_days_with_zero(project):
    add_event(project, datetime(2026, 9, 1, 9, 0, tzinfo=UTC))
    add_event(project, datetime(2026, 9, 1, 17, 0, tzinfo=UTC))
    add_event(project, datetime(2026, 9, 3, 12, 0, tzinfo=UTC))

    result = trends(project, "signed_up", date(2026, 9, 1), date(2026, 9, 3))

    assert len(result) == 1
    assert result[0]["breakdown_value"] is None
    assert result[0]["data"] == [
        {"day": date(2026, 9, 1), "count": 2},
        {"day": date(2026, 9, 2), "count": 0},
        {"day": date(2026, 9, 3), "count": 1},
    ]


def test_trends_date_range_is_inclusive_of_both_ends(project):
    add_event(project, datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC))
    add_event(project, datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC))
    add_event(project, datetime(2026, 9, 2, 23, 59, 59, tzinfo=UTC))
    add_event(project, datetime(2026, 9, 3, 0, 0, 0, tzinfo=UTC))

    result = trends(project, "signed_up", date(2026, 9, 1), date(2026, 9, 2))

    assert counts(result[0]) == [1, 1]


def test_trends_only_counts_the_requested_event_and_project(project):
    other_project = Project.objects.create(name="Other")
    when = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    add_event(project, when)
    add_event(project, when, event="$pageview")
    add_event(other_project, when)

    result = trends(project, "signed_up", date(2026, 9, 1), date(2026, 9, 1))

    assert counts(result[0]) == [1]


def test_trends_unique_users_counts_each_person_once_per_day(project):
    when = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    add_event(project, when, distinct_id="user_1")
    add_event(project, when, distinct_id="user_1")
    add_event(project, when, distinct_id="user_2")

    result = trends(project, "signed_up", date(2026, 9, 1), date(2026, 9, 1), math="unique_users")

    assert counts(result[0]) == [2]


def test_trends_breakdown_returns_one_series_per_value_largest_first(project):
    when = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    add_event(project, when, plan="pro")
    add_event(project, when, plan="free")
    add_event(project, when, plan="free")
    add_event(project, when)

    result = trends(project, "signed_up", date(2026, 9, 1), date(2026, 9, 1), breakdown="plan")

    assert [(s["breakdown_value"], counts(s)) for s in result] == [
        ("free", [2]),
        ("pro", [1]),
        (None, [1]),
    ]


def test_trends_with_no_events_returns_one_series_of_zeros(project):
    result = trends(project, "signed_up", date(2026, 9, 1), date(2026, 9, 3))

    assert counts(result[0]) == [0, 0, 0]
    assert len(result) == 1


@pytest.mark.parametrize("days", [1, 365])
def test_trends_runs_one_query_regardless_of_range(project, django_assert_num_queries, days):
    date_from = date(2026, 1, 1)
    date_to = date_from + timedelta(days=days - 1)

    with django_assert_num_queries(1):
        trends(project, "signed_up", date_from, date_to, breakdown="plan")
