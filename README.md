# AI Code Assistant

A production-grade AI coding assistant web application. This project is built
incrementally across phases:

- **Phase 1** — Application Foundation: Flask application factory,
  PostgreSQL-backed models, Dockerized deployment, CI pipelines, and a test
  suite.
- **Phase 2** — Authentication & User Management: registration, login,
  logout, password hashing, and account management.
- **Phase 3** — AI Core Features: chat interface with streaming responses,
  prompt library, AI code generation and analysis tools, file upload, and
  conversation management.

> **Status:** Phase 3 — AI core features implemented.

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

### Phase 2 — Authentication & user management

- **Registration** — create an account with a username and email; validates
  username length, email format, password strength (minimum 8 characters),
  password confirmation, and uniqueness of both username and email.
- **Login & logout** — email/password authentication with a remember-me
  option, last-login timestamp tracking, and disabled-account detection.
- **Password security** — salted password hashes via Werkzeug
  (`generate_password_hash` / `check_password_hash`); plain text is never
  stored.
- **Session management** — Flask-Login sessions with `@login_required`
  protection on authenticated routes and a shared account page (`/auth/me`).
- **Safe redirects** — post-login redirects are validated against an
  open-redirect attack (only same-host URLs are allowed).
- **CSRF protection** — all state-changing forms are protected via Flask-WTF.

### Phase 3 — AI core features

- **AI chat interface** — per-user conversations, message history, live
  server-sent-event (SSE) streaming, typing indicator, and client-side
  Markdown rendering with code blocks.
- **Prompt management** — save, edit, delete, favorite, categorize, and search
  reusable prompt templates.
- **AI code generation** — generate code from natural language, plus code
  actions: explain, refactor, find bugs, optimize, add comments, write
  documentation, and draft commit messages.
- **File support** — upload source files and run AI analysis over their
  contents (multi-language, UTF-8 text).
- **Conversation management** — rename, pin, search, delete, and export
  conversations as JSON.
- **Provider abstraction** — a provider-agnostic LLM service layer with an
  offline **mock provider** (default) and an OpenAI-compatible client. Set
  `LLM_PROVIDER=openai` and `OPENAI_API_KEY` for real responses.

## Tech stack

| Layer        | Technology                                        |
| ------------ | ------------------------------------------------- |
| Backend      | Python 3.12, Flask 3                              |
| Database     | PostgreSQL 16 (SQLite fallback for local dev)     |
| Auth         | Flask-Login, Flask-WTF, Werkzeug hashing          |
| Migrations   | Flask-Migrate (Alembic)                           |
| AI providers | Provider-agnostic service layer (mock + OpenAI)   |
| Frontend     | HTML, vanilla CSS, vanilla JavaScript (SSE)       |
| Infrastructure | Docker, Docker Compose, GitHub Actions          |
| Quality      | pytest, ruff, black                               |

## Project structure

```
.
├── .github/workflows/     # GitHub Actions CI pipelines
├── app/
│   ├── auth/              # Authentication blueprint (register/login/logout)
│   ├── chat/              # Chat blueprint (conversations, SSE streaming)
│   ├── main/              # Public routes, landing page, health check
│   ├── models/            # SQLAlchemy models (User, Conversation, Message, Prompt)
│   ├── prompts/           # Prompt library blueprint (CRUD, search, favorites)
│   ├── services/          # Service layer (LLM providers)
│   ├── static/            # CSS and JavaScript assets
│   ├── templates/         # Jinja2 templates (pages + error pages)
│   ├── tools/             # AI tools blueprint (generate, analyze, actions)
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
| `LLM_PROVIDER`       | `mock`       | LLM backend: `mock` (offline) or `openai`|
| `OPENAI_API_KEY`     | unset        | API key for the OpenAI provider          |
| `OPENAI_BASE_URL`    | OpenAI       | Custom/compatible endpoint               |
| `OPENAI_MODEL`       | `gpt-4o-mini`| Model used by the OpenAI provider        |
| `MAX_CONTENT_LENGTH` | `16777216`   | Max uploaded file size in bytes          |

The production configuration fails fast at startup if `SECRET_KEY` or a
PostgreSQL `DATABASE_URL` is missing — it will never silently run with
insecure defaults.

> The app runs fully offline with the default **mock provider**: chat replies,
> code generation, and file analysis all work with canned responses. To enable
> real AI responses set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` (or point
> `OPENAI_BASE_URL` at an OpenAI-compatible server).

## CI / CD

GitHub Actions runs on every push to `main` and on pull requests:

1. **Lint & format** — `ruff check` and `black --check`.
2. **Tests** — `pytest` with coverage reporting.
3. **Docker** — verifies the production image builds successfully.

## Roadmap

Planned phases (tracked as GitHub issues):

- **Phase 4** — Production hardening: token usage tracking, rate limiting,
  retries, API-key encryption, prompt-injection hardening, and audit logging.
- **Phase 5** — Workspaces, projects, and file storage.
- **Phase 6** — Real-time collaboration, code review, and quality tooling.

## License

[MIT](./LICENSE)
