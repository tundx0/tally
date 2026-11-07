from datetime import date, timedelta

import pytest
from django.http import QueryDict
from django.utils import timezone

from analytics.serializers import TrendsQuerySerializer


def test_trends_query_defaults_to_last_7_days_and_total():
    serializer = TrendsQuerySerializer(data={"event": "signed_up"})

    assert serializer.is_valid(), serializer.errors
    today = timezone.now().date()
    assert serializer.validated_data == {
        "event": "signed_up",
        "date_from": today - timedelta(days=6),
        "date_to": today,
        "breakdown": None,
        "math": "total",
    }


def test_trends_query_accepts_a_real_query_string():
    params = QueryDict(
        "event=signed_up&date_from=2026-09-01&date_to=2026-09-30&breakdown=plan&math=unique_users"
    )
    serializer = TrendsQuerySerializer(data=params)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["date_from"] == date(2026, 9, 1)
    assert serializer.validated_data["breakdown"] == "plan"


def test_trends_query_with_only_date_to_starts_6_days_earlier():
    serializer = TrendsQuerySerializer(data={"event": "signed_up", "date_to": "2026-09-30"})

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["date_from"] == date(2026, 9, 24)


def test_trends_query_allows_exactly_365_days():
    serializer = TrendsQuerySerializer(
        data={"event": "signed_up", "date_from": "2026-01-01", "date_to": "2026-12-31"}
    )

    assert serializer.is_valid(), serializer.errors


@pytest.mark.parametrize(
    ("params", "error_field"),
    [
        ({}, "event"),
        ({"event": ""}, "event"),
        ({"event": "signed_up", "math": "avg"}, "math"),
        ({"event": "signed_up", "date_from": "09/01/2026"}, "date_from"),
        ({"event": "signed_up", "breakdown": ""}, "breakdown"),
        ({"event": "signed_up", "breakdown": "plan__name"}, "breakdown"),
        (
            {"event": "signed_up", "date_from": "2026-09-05", "date_to": "2026-09-01"},
            "non_field_errors",
        ),
        (
            {"event": "signed_up", "date_from": "2025-12-31", "date_to": "2026-12-31"},
            "non_field_errors",
        ),
    ],
)
def test_trends_query_rejects_invalid_params(params, error_field):
    serializer = TrendsQuerySerializer(data=params)

    assert not serializer.is_valid()
    assert error_field in serializer.errors
