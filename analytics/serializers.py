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
