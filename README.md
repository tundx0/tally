# tally

Event analytics backend in Django + DRF: event ingestion today, with trends and an MCP server for agents in progress.

## Stack

Django + Django REST Framework, Postgres, Celery + Redis, pytest, ruff, managed with [uv](https://docs.astral.sh/uv/).

## Getting started

```bash
cp .env.example .env              # then set a real SECRET_KEY
docker compose up -d --wait       # Postgres on :5442, Redis on :6392
uv sync                           # create .venv and install deps
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- Admin: http://localhost:8000/admin/
- Health check: http://localhost:8000/api/health/

Background worker (in a second terminal):

```bash
uv run celery -A config worker -l info
```

## Everyday commands

| Task | Command |
|---|---|
| Run tests | `uv run pytest` |
| Lint / format | `uv run ruff check . --fix && uv run ruff format .` |
| New migration after editing models | `uv run python manage.py makemigrations` |
| See the SQL a migration runs | `uv run python manage.py sqlmigrate analytics 0001` |
| Interactive shell with models loaded | `uv run python manage.py shell` |

## Layout

```
config/       project wiring: settings, root urls, celery
accounts/     custom User model
analytics/    Project, Person, Event models, admin, API
conftest.py   shared pytest fixtures
```

## Sending events

Client apps send events to Tally with `POST /api/capture/`. Each request carries a batch of 1 to 1,000 events, and every event is stored in the project that owns the request's API key.

### Request

The body is a JSON object with two fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `api_key` | string | yes | Identifies the project the events belong to. Starts with `phc_`; find it on the project's page in the admin. The key is public: it can only send events, never read them. |
| `batch` | array | yes | The events to store: 1 to 1,000 per request. |

Each event in `batch`:

| Field | Type | Required | Description |
|---|---|---|---|
| `event` | string | yes | What happened, e.g. `signed_up` or `$pageview`. Up to 200 characters. |
| `distinct_id` | string | yes | Your app's ID for the user who did it, e.g. `user-42`. Up to 200 characters. |
| `timestamp` | ISO 8601 string | no | When it happened, e.g. `2026-09-30T10:00:00Z`. Times without a timezone are read as UTC. Defaults to the time Tally received the request. |
| `properties` | object | no | Any extra data about the event, e.g. `{"plan": "pro"}`. Must be a JSON object, not a list. Defaults to `{}`. |

### Example

```bash
curl -X POST http://localhost:8000/api/capture/ \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "phc_your_key",
    "batch": [
      {"event": "signed_up", "distinct_id": "user-42", "properties": {"plan": "pro"}},
      {"event": "$pageview", "distinct_id": "user-42", "timestamp": "2026-09-30T10:00:00Z"}
    ]
  }'
```

```json
{"accepted": 2}
```

The path must end with a slash. Without it, Django redirects the request, and most HTTP clients follow the redirect as a `GET` without the body.

### Responses

| Status | When | Body |
|---|---|---|
| `200` | Every event in the batch was stored. | `{"accepted": <count>}` |
| `400` | The batch is invalid: a missing or blank `event` or `distinct_id`, a value over 200 characters, an unreadable `timestamp`, `properties` that isn't an object, or a batch that is empty or over 1,000 events. | Errors keyed by field, with event errors keyed by the event's position in the batch, e.g. `{"batch": {"1": {"event": ["This field is required."]}}}` |
| `401` | `api_key` is missing or doesn't match a project. Includes the header `WWW-Authenticate: ApiKey realm="api"`. | `{"detail": "Missing api_key."}` or `{"detail": "Invalid api_key."}` |
| `405` | Any method other than `POST`. | `{"detail": "Method \"GET\" not allowed."}` |

### Behavior

- **Batches are all-or-nothing.** If any event is invalid, the request returns `400` and nothing from the batch is stored.
- **Persons are created automatically.** The first event for a new `distinct_id` creates a `Person` in the project. Existing persons are never duplicated or modified.
- **The cost doesn't grow with batch size.** Every successful request makes 3 database queries (key lookup, person insert, event insert), whether it carries 1 event or 1,000. A test enforces this.
- **Capture is at-least-once.** If the response is lost after the events are stored and the client retries, the events are stored twice. Per-event IDs for deduplication are planned.
