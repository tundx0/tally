# tally

Event analytics backend in Django + DRF: ingestion, trends, and an MCP server for agents.

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
