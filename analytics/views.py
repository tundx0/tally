from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import ProjectApiKeyAuthentication
from .models import Event
from .serializers import CaptureSerializer


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

        Event.objects.bulk_create(events)

        return Response({"accepted": len(events)})
