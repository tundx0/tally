import io
from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

from analytics.models import Event, Person, Project


def test_seed_events_creates_events_and_persons(db):
    output = io.StringIO()

    call_command("seed_events", events=50, users=10, days=7, seed=1, stdout=output)

    project = Project.objects.get(name="Project-1")
    assert Event.objects.filter(project=project).count() == 50
    assert Person.objects.filter(project=project).count() == 10
    week_ago = timezone.now() - timedelta(days=7)
    assert not Event.objects.filter(project=project, timestamp__lt=week_ago).exists()
    assert "Done: 50 events" in output.getvalue()


def test_seed_events_is_repeatable_with_a_seed(db):
    call_command("seed_events", project="A", events=20, users=5, seed=42, stdout=io.StringIO())
    call_command("seed_events", project="B", events=20, users=5, seed=42, stdout=io.StringIO())

    def rows(name):
        events = Event.objects.filter(project__name=name).order_by("id")
        return list(events.values_list("event", "distinct_id", "properties"))

    assert rows("A") == rows("B")
