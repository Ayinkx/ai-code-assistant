# AI Code Assistant

A production-grade AI coding assistant web application. This project is built
incrementally across phases — **Phase 1** delivers the full application
foundation: Flask application factory, PostgreSQL-backed models, user
authentication scaffolding, Dockerized deployment, CI pipelines, and a test
suite.

> **Status:** Phase 1 — foundation and authentication scaffolding.

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
  - [Local development](#local-development)
  - [Running with Docker](#running-with-docker)
- [Testing](#testing)
- [Configuration](#configuration)
- [CI / CD](#ci--cd)
- [Roadmap](#roadmap)
- [License](#license)

## Features

- **Flask application factory** — testable, environment-driven configuration.
- **User authentication** — registration, login, logout, remember-me, session
  management, and CSRF protection via Flask-WTF.
- **Secure password storage** — salted hashes via Werkzeug (never plain text).
- **PostgreSQL-first persistence** — SQLAlchemy models with Flask-Migrate
  schema migrations.
- **Containerized** — multi-stage `Dockerfile`, `docker-compose` with a
  health-checked Postgres service, and a non-root runtime user.
- **CI pipeline** — lint (ruff), formatting (black), tests (pytest), and
  Docker image build on every push/PR.
- **Clean UI** — dark, developer-focused theme with responsive vanilla CSS and
  progressive-enhancement JavaScript.

## Tech stack

| Layer        | Technology                                        |
| ------------ | ------------------------------------------------- |
| Backend      | Python 3.12, Flask 3                              |
| Database     | PostgreSQL 16 (SQLite fallback for local dev)     |
| Auth         | Flask-Login, Flask-WTF, Werkzeug hashing          |
| Migrations   | Flask-Migrate (Alembic)                           |
| Frontend     | HTML, vanilla CSS, vanilla JavaScript             |
| Infrastructure | Docker, Docker Compose, GitHub Actions          |
| Quality      | pytest, ruff, black                               |

## Project structure

```
.
├── .github/workflows/     # GitHub Actions CI pipelines
├── app/
│   ├── auth/              # Authentication blueprint (register/login/logout)
│   ├── main/              # Public routes, landing page, health check
│   ├── models/            # SQLAlchemy models (User)
│   ├── static/            # CSS and JavaScript assets
│   ├── templates/         # Jinja2 templates (pages + error pages)
│   ├── config.py          # Environment-based configuration
│   ├── extensions.py      # Shared Flask extension instances
│   └── __init__.py        # Application factory
├── migrations/            # Alembic migration scripts (generated)
├── scripts/               # Operational helper scripts
├── tests/                 # pytest suite
├── Dockerfile             # Multi-stage production image
├── docker-compose.yml     # web + postgres orchestration
├── pyproject.toml         # Tooling configuration (pytest, ruff, black)
└── requirements*.txt      # Python dependencies
```

## Getting started

### Prerequisites

- Python 3.12+
- PostgreSQL 16 (optional — SQLite is used by default in development)
- Docker + Docker Compose (optional, for containerized runs)
- Git

### Local development

```bash
# 1. Clone and enter the project
git clone https://github.com/your-org/ai-code-assistant.git
cd ai-code-assistant

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Configure environment
cp .env.example .env             # then edit values as needed

# 5. Create the database tables (uses SQLite by default)
flask --app wsgi init-db

# 6. Run the dev server
python run.py
```

Open <http://localhost:5000> in your browser.

### Running with Docker

```bash
cp .env.example .env
docker compose up --build
```

- Web app: <http://localhost:5000>
- PostgreSQL: `localhost:5432` (user `aica`, db `aica`)

The `web` service applies pending migrations before starting, and exposes a
health check at `GET /health`.

## Testing

```bash
pytest --cov=app --cov-report=term-missing
```

Tests run against an in-memory SQLite database so the suite is fast and
self-contained. Set `TEST_DATABASE_URL` to a PostgreSQL URL to run the same
suite against Postgres.

## Configuration

All configuration is environment-driven (see `.env.example`):

| Variable             | Default      | Description                              |
| -------------------- | ------------ | ---------------------------------------- |
| `APP_ENV`            | `development`| `development`, `testing`, or `production`|
| `SECRET_KEY`         | dev-only     | Flask secret — **required in production** |
| `DATABASE_URL`       | SQLite file  | SQLAlchemy connection string             |
| `SESSION_LIFETIME`   | `43200`      | Session lifetime in seconds              |

The production configuration fails fast at startup if `SECRET_KEY` or a
PostgreSQL `DATABASE_URL` is missing — it will never silently run with
insecure defaults.

## CI / CD

GitHub Actions runs on every push to `main` and on pull requests:

1. **Lint & format** — `ruff check` and `black --check`.
2. **Tests** — `pytest` with coverage reporting.
3. **Docker** — verifies the production image builds successfully.

## Roadmap

Planned phases (tracked as GitHub issues):

- **Phase 2** — AI assistant chat UI, message persistence, API keys, streaming
  responses, and provider integration (OpenAI/Anthropic).
- **Phase 3** — Workspaces, projects, file storage, and session history.
- **Phase 4** — Real-time collaboration, code review, and quality tooling.

## License

[MIT](./LICENSE)
