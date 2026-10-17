from datetime import UTC, datetime, time, timedelta

from django.db.models import Count
from django.db.models.fields.json import KT
from django.db.models.functions import TruncDate

from .models import Event


def trends(project, event, date_from, date_to, breakdown=None, math="total"):
    """Count `event` per day from date_from to date_to (inclusive, UTC days).

    Returns one series per breakdown value, each with an entry for every day,
    including days with no events.
    """
    start = datetime.combine(date_from, time.min, tzinfo=UTC)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)

    events = Event.objects.filter(
        project=project, event=event, timestamp__gte=start, timestamp__lt=end
    )

    group_by = ["day"]
    if breakdown:
        events = events.annotate(breakdown_value=KT(f"properties__{breakdown}"))
        group_by.append("breakdown_value")

    if math == "unique_users":
        metric = Count("distinct_id", distinct=True)
    else:
        metric = Count("id")

    rows = (
        events.annotate(day=TruncDate("timestamp"))
        .values(*group_by)
        .annotate(count=metric)
        .order_by(*group_by)
    )

    counts = {}
    for row in rows:
        value = row.get("breakdown_value")
        counts.setdefault(value, {})[row["day"]] = row["count"]

    if not breakdown and not counts:
        counts[None] = {}
    days = [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]
    series = sorted(counts.items(), key=lambda item: sum(item[1].values()), reverse=True)

    return [
        {
            "breakdown_value": value,
            "data": [{"day": day, "count": by_day.get(day, 0)} for day in days],
        }
        for value, by_day in series
    ]
