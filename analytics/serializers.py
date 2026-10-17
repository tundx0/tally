from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers


class EventInputSerializer(serializers.Serializer):
    # Why a ModelSerializer was not used? This is because it copies all the fields in the model
    # which will enable a user/client send an event to any project it named. The project(tenant)
    # must come from the API key.
    event = serializers.CharField(max_length=200)
    distinct_id = serializers.CharField(max_length=200)
    timestamp = serializers.DateTimeField(required=False)
    properties = serializers.DictField(default=dict)

    # Why not JSONField? JSONField will accept any valid JSON value like lists, strings but
    # DictField only accepts a JSON object also a function dict was passed to default instead of {}
    # avoiding a shared mutable default bug.


class CaptureSerializer(serializers.Serializer):
    # Why max_length=1000? It caps the batch size so one request can't send an unbounded list
    # (e.g. a 50 MB body) that ties up the server and the database insert.
    # PyCharm flags it as an unexpected argument, but it is valid: with many=True, DRF's __new__
    # builds a ListSerializer and hands max_length (and allow_empty) to it, not to this class.

    # noinspection PyArgumentList
    batch = EventInputSerializer(many=True, allow_empty=False, max_length=1000)


MAX_TRENDS_DAYS = 365
DEFAULT_TRENDS_DAYS = 7


class TrendsQuerySerializer(serializers.Serializer):
    event = serializers.CharField(max_length=200)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    breakdown = serializers.CharField(max_length=200, default=None)
    math = serializers.ChoiceField(choices=["total", "unique_users"], default="total")

    def validate_breakdown(self, value):
        if value is not None and "__" in value:
            raise serializers.ValidationError("Property names must not contain '__'.")
        return value

    def validate(self, attrs):
        date_to = attrs.get("date_to") or timezone.now().date()
        # Minus 1 because the range includes date_to: the last 7 days = today + the 6 before it.
        date_from = attrs.get("date_from") or date_to - timedelta(
            days=DEFAULT_TRENDS_DAYS - 1
        )
        if date_from > date_to:
            raise serializers.ValidationError("date_from must be before date_to.")
        if (date_to - date_from).days + 1 > MAX_TRENDS_DAYS:
            raise serializers.ValidationError(
                f"This date range cannot be longer than {MAX_TRENDS_DAYS} days."
            )
        attrs["date_from"] = date_from
        attrs["date_to"] = date_to
        return attrs
