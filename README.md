# tally

Event analytics backend in Django + DRF. It takes in events and answers daily trends questions about them. An MCP server for agents is next.

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
| Fill the database with fake events | `uv run python manage.py seed_events --events 1000000 --seed 1` |

## Test data

`seed_events` fills a project with realistic fake events, so you can try queries and measure performance on real volumes. Run it against your local database only.

```bash
uv run python manage.py seed_events --events 1000000 --seed 1
```

One million events take about a minute. The command prints its progress after every batch.

What it creates:

- **The project**, if no project with that name exists yet.
- **One `Person` per user**, `user-1` to `user-<N>`. Existing persons are skipped.
- **Events spread evenly over the last N days**, from random users, in realistic proportions: 80% `$pageview`, 10% `signed_up`, 5% `upgraded`, 5% `invited_teammate`.
- **Properties on every event:** `$browser` is always set. `plan` (`free`, `pro` or `enterprise`) is set on 90% of events, so breakdowns always include a group with no value.

| Option | Default | Description |
|---|---|---|
| `--project` | `Project-1` | Name of the project to add events to. |
| `--events` | `100000` | How many events to create. |
| `--days` | `90` | Spread events over this many days before now. |
| `--users` | `5000` | How many distinct users the events come from. |
| `--batch-size` | `10000` | Events per database insert. Larger batches are faster but use more memory. |
| `--seed` | random | Makes the data repeatable: the same seed always creates the same events. Use one when comparing performance before and after a change. |

Running the command again adds more events to the same project. To start over, use a new `--project` name.

## Layout

```
config/       project wiring: settings, root urls, celery
accounts/     custom User model
analytics/    Project, Person, Event models, admin, capture and trends API, seed_events command
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

## Reading trends

Trends answers questions like "how many people signed up each day this month, and on which plan?" It counts one event per day for a project. Only members of that project can call it.

```
GET /api/projects/<project_id>/trends/
```

### Access

You need a logged-in Django session, and your user has to be a member of the project. Log in at `/api-auth/login/` or through the admin, and add members on the project's page in the admin.

Logged out, you get `403`. Logged in but not a member, you get `404`, which is the same response as for a project that doesn't exist. That's on purpose: someone outside a project can't find out which project IDs are real. The membership check also runs before the parameters are validated, so a non-member gets `404` even for a malformed request.

### Query parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `event` | yes | | The event to count, e.g. `signed_up`. Up to 200 characters. |
| `date_from` | no | 6 days before `date_to` | First day to include, as `YYYY-MM-DD`. |
| `date_to` | no | today | Last day to include, as `YYYY-MM-DD`. |
| `breakdown` | no | none | A property to split the counts by, e.g. `plan`. Can't contain `__`. |
| `math` | no | `total` | `total` counts events. `unique_users` counts distinct `distinct_id`s, so someone who signs up twice on the same day counts once. |

Both dates are included in the range. `date_from` can't be after `date_to`, and a range can cover at most 365 days. Days are UTC days. If you send only `event`, you get the last 7 days, today included.

### Example

Logged in as a member, open:

```
http://localhost:8000/api/projects/4/trends/?event=signed_up&date_from=2026-11-01&date_to=2026-11-03&breakdown=plan
```

```json
{
  "event": "signed_up",
  "date_from": "2026-11-01",
  "date_to": "2026-11-03",
  "breakdown": "plan",
  "math": "total",
  "series": [
    {"breakdown_value": "enterprise", "data": [{"day": "2026-11-01", "count": 361}, {"day": "2026-11-02", "count": 336}, {"day": "2026-11-03", "count": 347}]},
    {"breakdown_value": "free", "data": [{"day": "2026-11-01", "count": 353}, {"day": "2026-11-02", "count": 338}, {"day": "2026-11-03", "count": 337}]},
    {"breakdown_value": "pro", "data": [{"day": "2026-11-01", "count": 310}, {"day": "2026-11-02", "count": 319}, {"day": "2026-11-03", "count": 329}]},
    {"breakdown_value": null, "data": [{"day": "2026-11-01", "count": 102}, {"day": "2026-11-02", "count": 116}, {"day": "2026-11-03", "count": 123}]}
  ]
}
```

### Reading the response

The parameters come back with the defaults filled in, so you can always see which range and metric were counted, even ones you didn't send.

Each entry in `series` is one line on a chart, biggest total first. Events that don't have the breakdown property are grouped under `"breakdown_value": null`. In the example, that's the sign-ups with no `plan`. Without a breakdown you get a single series, also with `breakdown_value` set to `null`.

Every day in the range is in `data`, including days with a count of 0. A chart drawn from it never skips a quiet day.

### Errors

| Status | When | Body |
|---|---|---|
| `400` | A parameter is missing or invalid: no `event`, a date that isn't `YYYY-MM-DD`, `date_from` after `date_to`, a range over 365 days, an unknown `math` value, or a `breakdown` containing `__`. | Errors keyed by parameter, e.g. `{"event": ["This field is required."]}`. Problems with the date range come under `non_field_errors`. |
| `403` | You're not logged in. | `{"detail": "Authentication credentials were not provided."}` |
| `404` | The project doesn't exist, or you aren't a member of it. | `{"detail": "No Project matches the given query."}` |
| `405` | `POST`, `PUT`, `PATCH` or `DELETE`. | `{"detail": "Method \"POST\" not allowed."}` |

## Performance

How fast the trends query is on 1,000,000 events, and what made it faster.

The numbers come from one project with 1,000,000 events from `seed_events --events 1000000 --seed 1` (90 days, 5,000 users; 2,000,217 rows in the table in total). Postgres 17.11 in Docker on an Apple M1 Pro with 32 GB, default `work_mem` (4 MB). Each query ran once to warm the cache, then three times; times are the median `Execution Time` from `EXPLAIN (ANALYZE, BUFFERS)`.

| Query | Rows counted | Plan | Pages read | Time |
|---|---|---|---|---|
| `signed_up`, 30 days | 32,250 | Index Only Scan | 261 | 12 ms |
| `signed_up`, 30 days, `breakdown=plan` | 32,250 | Index Scan | 32,507 | 36 ms |
| `signed_up`, 30 days, `math=unique_users` | 32,250 | Index Scan | 32,507 | 80 ms |
| `$pageview`, 7 days | 53,635 | Index Only Scan | 437 | 20 ms |
| `$pageview`, 90 days | 791,663 | Index Only Scan, sort spills to disk | 6,130 | 352 ms |

### What made total counts faster

Total counts use `COUNT(*)` instead of `COUNT(id)`. The `(project, event, timestamp)` index holds every column a total count needs, but not `id`, so `COUNT(id)` made Postgres fetch every matching row from the table. With `COUNT(*)`, it answers from the index alone:

| `signed_up`, 30 days | Plan | Pages read | Time |
|---|---|---|---|
| `COUNT(id)` | Index Scan | 32,507 | 33 ms |
| `COUNT(*)` | Index Only Scan | 261 | 12 ms |

That's 125 times fewer pages and about 2.8 times faster, with the same results. Index-only scans also need Postgres's visibility map to be current. I expected to run `VACUUM` by hand for that, but autovacuum had already done it two seconds after the seed finished.

### Where it is still slow

Breakdowns and unique users need `properties` and `distinct_id`, which aren't in the index, so Postgres reads every matching row from the table. Putting those columns in the index would speed that up, but the index would get much bigger and every capture insert slower. At 36 and 80 ms, I don't think that trade is worth it yet.

The worst case is a common event over a wide range. `$pageview` over 90 days covers 79% of the project's events, and sorting 791,663 rows doesn't fit in the default 4 MB of `work_mem`, so the sort spills to disk. This is the one query where `COUNT(id)` came out ahead (283 ms), because Postgres split its sequential scan across three processes while the index-only scan ran in one. Give the sort 64 MB and it stays in memory, and the result flips: 275 ms for `COUNT(*)`, 501 ms for `COUNT(id)`. I didn't raise `work_mem` globally, since that limit applies to every sort on every connection.

The seeded data also makes things look a bit worse than they'd be in production. `seed_events` gives events random timestamps, so a single day's events end up scattered across the table. Real events arrive roughly in time order and sit next to each other on disk, which helps the queries that read table rows.

Past this size, counting hundreds of thousands of rows for every chart is the wrong job for Postgres. I'd either pre-aggregate daily counts or move events to a columnar database like ClickHouse, which only reads the columns a query uses.
