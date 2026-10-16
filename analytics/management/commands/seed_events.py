import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import Event, Person, Project

EVENT_NAMES = ["$pageview", "signed_up", "upgraded", "invited_teammate"]
EVENT_WEIGHTS = [80, 10, 5, 5]
PLANS = ["free", "pro", "enterprise"]
BROWSERS = ["Chrome", "Safari", "Firefox"]


def make_event(rng, project, now, max_seconds, users):
    properties = {"$browser": rng.choice(BROWSERS)}
    if rng.random() < 0.9:
        properties["plan"] = rng.choice(PLANS)
    return Event(
        project=project,
        event=rng.choices(EVENT_NAMES, weights=EVENT_WEIGHTS)[0],
        distinct_id=f"user-{rng.randint(1, users)}",
        properties=properties,
        timestamp=now - timedelta(seconds=rng.randint(0, max_seconds)),
    )


class Command(BaseCommand):
    help = "Create events in local project for testing and benchmarking purposes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project", default="Project-1", help="Project name created if missing."
        )
        parser.add_argument(
            "--events", type=int, default=100_000, help="How many events to be created."
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="How many days do you want to spread events over?.",
        )
        parser.add_argument("--users", type=int, default=5_000, help="How many distinct users.")
        parser.add_argument("--batch-size", type=int, default=10_000, help="Events per INSERT.")
        parser.add_argument("--seed", type=int, help="Random seed, for repeatable data.")

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        project, _ = Project.objects.get_or_create(name=options["project"])
        now = timezone.now()
        total = options["events"]
        max_seconds = options["days"] * 24 * 60 * 60

        Person.objects.bulk_create(
            [
                Person(project=project, distinct_id=f"user-{i}")
                for i in range(1, options["users"] + 1)
            ],
            ignore_conflicts=True,
        )
        created = 0
        while created < total:
            size = min(options["batch_size"], total - created)
            Event.objects.bulk_create(
                [make_event(rng, project, now, max_seconds, options["users"]) for _ in range(size)]
            )
            created += size
            self.stdout.write(f"{created:,} / {total:,} events")
        self.stdout.write(self.style.SUCCESS(f"Done: {total:,} events in '{project.name}'."))
