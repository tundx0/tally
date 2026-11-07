from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import ProjectApiKeyAuthentication
from .models import Event, Person, Project
from .serializers import CaptureSerializer, TrendsQuerySerializer
from .trends import trends


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


class CaptureView(APIView):
    """Receives batches of events from client SDKs"""

    authentication_classes = [ProjectApiKeyAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = request.auth
        now = timezone.now()

        events = [
            Event(
                project=project,
                event=item["event"],
                distinct_id=item["distinct_id"],
                properties=item["properties"],
                timestamp=item.get("timestamp", now),
            )
            for item in serializer.validated_data["batch"]
        ]

        # Why save persons before events? These are two separate INSERTs, so a crash between
        # them leaves a partial write. This order makes that partial write safe to retry:
        # - Persons first: a retry skips the existing persons (ignore_conflicts) and saves the
        #   events, so the end result is clean.
        # - Events first: a retry would save the same events a second time (duplicates).
        # That is simpler than wrapping both INSERTs in a transaction.
        # Note: this only covers a crash between the two INSERTs. Capture as a whole is
        # at-least-once: a retry after a lost response still duplicates events.
        distinct_ids = sorted({event.distinct_id for event in events})
        Person.objects.bulk_create(
            [Person(project=project, distinct_id=distinct_id) for distinct_id in distinct_ids],
            ignore_conflicts=True,
        )

        Event.objects.bulk_create(events)

        return Response({"accepted": len(events)})


class TrendsView(APIView):
    """Daily counts of one event for a project the user is a member of."""

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)

        query = TrendsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        return Response({**params, "series": trends(project, **params)})
