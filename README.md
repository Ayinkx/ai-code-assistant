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
- **Phase 4** — GitHub Integration & Repository Intelligence: OAuth connection,
  repository browser, commit history, issues and pull requests with AI
  analysis, and encrypted token storage.
- **Phase 5** — AI Workspaces & Project Intelligence: workspace CRUD, project
  import (GitHub or archive upload), lazy file explorer, project-wide search,
  AI project chat and analyses, and a project health dashboard.

> **Status:** Phase 5 — Workspaces and project intelligence implemented.

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

### Phase 4 — GitHub integration & repository intelligence

- **GitHub OAuth connection** — connect/disconnect a GitHub account through a
  browser OAuth flow (scoped to `read:user repo`), with a signed state
  parameter to prevent CSRF on the callback.
- **Encrypted token storage** — access tokens are encrypted at rest with
  Fernet (AES-128 + HMAC-SHA256) using a key derived from `SECRET_KEY`; the
  plaintext token is never persisted, logged, or sent to the frontend.
- **Repository browser** — list and search repositories, browse branches and
  files (directory listing and tree view), search file names, and view file
  contents.
- **Commit history** — per-repository and per-path commit lists with author,
  date, and per-commit file/patch views.
- **Issues** — open/closed/all issue lists (pull requests excluded), issue
  detail pages with labels and body, and one-click **AI issue analysis**
  (summary, problem identification, suggested implementation, acceptance
  criteria, difficulty estimate).
- **Pull requests** — PR lists and detail pages with changed files and inline
  diffs, plus **AI code review** that flags potential bugs while clearly
  labeling `[CONFIRMED]` defects versus `[SUGGESTION]` hypotheses.
- **AI repository analysis** — summarize a repository from its README and
  structure, and ask questions about individual files. Context sent to the
  model is bounded (`GITHUB_MAX_CONTEXT_CHARS`) so a request never uploads a
  whole repository.
- **API reliability** — a dedicated GitHub API client with request timeouts,
  typed error taxonomy (auth, permission, not-found, rate-limit, network),
  exponential backoff retries on transient failures, and rate-limit awareness.
- **Authorization** — all GitHub API calls are made on the user's behalf with
  their own token, so GitHub's own permission model decides which
  repositories are accessible; no secrets are ever exposed to the client.

### Phase 5 — AI workspaces & project intelligence

- **Workspaces** — per-user workspaces with create, rename, delete, and a
  dashboard listing projects with import status.
- **Project import** — import a codebase from a connected GitHub repository
  or an uploaded `.zip` / `.tar.gz` archive. GitHub imports walk the blob
  tree and fetch bounded file contents; archive extraction is done entirely
  in memory (nothing is written to disk).
- **Import security** — archive members with absolute paths, `..` traversal,
  or symlinks are rejected/skipped; archive size, expanded size, and
  file-count caps (zip-bomb protection); VCS/vendor directories and secret
  files (`.env`, `.pem`, `.key`, …) are skipped; binary and oversized files
  keep metadata but no searchable content.
- **Lazy file explorer** — tree and single-file APIs load directories on
  demand and reject traversal paths; the file viewer shows language, size,
  and content with binary/oversized markers.
- **Project-wide search** — bounded filename and content search with literal
  (escaped) matching, case toggle, and match snippets; binary files are
  excluded from content hits.
- **AI project chat** — ask questions about the project; context is *bounded*
  (keyword-scored paths, key files, content fallback within a fixed character
  budget — never a whole-project dump) and available over SSE streaming.
- **AI analyses** — architecture, bug review, refactoring, test coverage,
  documentation, and dependency analyses. Findings are labeled
  `[CONFIRMED]` (supported by the files) versus `[SUGGESTION]` (inference).
- **Dependency inventory** — real manifests are parsed (`requirements.txt`,
  `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Pipfile`,
  `Gemfile`, `composer.json`); nothing is fabricated, and unpinned/insecure
  claims are surfaced only as `[SUGGESTION]`s.
- **Prompt-injection resistance** — repository file contents are explicitly
  framed as untrusted DATA in the system prompt, so instructions embedded in
  imported files are not followed.
- **Health dashboard** — per-project stats: file/searchable/test/doc counts,
  languages, dependency count, manifests, and indexing duration.

## Tech stack

| Layer        | Technology                                        |
| ------------ | ------------------------------------------------- |
| Backend      | Python 3.12, Flask 3                              |
| Database     | PostgreSQL 16 (SQLite fallback for local dev)     |
| Auth         | Flask-Login, Flask-WTF, Werkzeug hashing          |
| Migrations   | Flask-Migrate (Alembic)                           |
| AI providers | Provider-agnostic service layer (mock + OpenAI)   |
| GitHub       | GitHub REST API, OAuth web flow, Fernet (cryptography) |
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
│   ├── github/            # GitHub blueprint (OAuth, repo browser, issues, PRs)
│   ├── main/              # Public routes, landing page, health check
│   ├── models/            # SQLAlchemy models (User, GithubAccount, ...)
│   ├── prompts/           # Prompt library blueprint (CRUD, search, favorites)
│   ├── services/          # Service layer (LLM providers, GitHub API, crypto, import/search/analysis)
│   ├── static/            # CSS and JavaScript assets
│   ├── templates/         # Jinja2 templates (pages + error pages)
│   ├── tools/             # AI tools blueprint (generate, analyze, actions)
│   ├── workspaces/        # Workspaces & project intelligence blueprint (Phase 5)
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

### Setting up GitHub OAuth (Phase 4)

1. Create an OAuth App at <https://github.com/settings/applications/new>:
   - **Homepage URL:** `http://localhost:5000`
   - **Authorization callback URL:** `http://localhost:5000/github/callback`
2. Copy the **Client ID** and **Client Secret** into `.env`:
   ```bash
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```
3. Restart the app and open **GitHub** in the navigation bar to connect your
   account.

> Tokens are encrypted before storage and used only server-side; they are
> never exposed in the browser. To disconnect (and remove the stored token),
> use **Disconnect** on the GitHub dashboard.

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
| `GITHUB_CLIENT_ID`   | unset        | GitHub OAuth app client ID               |
| `GITHUB_CLIENT_SECRET`| unset       | GitHub OAuth app client secret           |
| `GITHUB_REDIRECT_URI`| callback URL | Explicit callback URL (optional)         |
| `GITHUB_API_URL`     | `https://api.github.com` | GitHub REST API base URL      |
| `GITHUB_SCOPES`      | `read:user repo` | OAuth scopes requested on connect    |
| `GITHUB_REQUEST_TIMEOUT` | `30`     | GitHub API request timeout (seconds)     |
| `GITHUB_MAX_CONTEXT_CHARS` | `40000` | Max repo context sent to the LLM       |
| `PROJECT_MAX_ARCHIVE_BYTES` | `52428800` | Max uploaded project archive (50 MB) |
| `PROJECT_MAX_SIZE_BYTES` | `524288000` | Max expanded project size (500 MB)   |
| `PROJECT_MAX_FILE_COUNT` | `20000`   | Max files importable into one project  |
| `PROJECT_MAX_FILE_CHARS` | `200000`  | Max text content stored per file       |
| `PROJECT_MAX_CONTEXT_CHARS` | `40000` | Max project context sent to the LLM  |
| `PROJECT_SEARCH_MAX_RESULTS` | `100` | Max results returned by one search query |
| `PROJECT_GITHUB_MAX_FILES` | `1000`   | Max file contents fetched per GitHub import |
| `PROJECT_SKIP_DIRS`    | `.git,node_modules,…` | Directory basenames skipped on import |
| `PROJECT_SKIP_SECRET_FILES` | `.env,.pem,…` | File names/prefixes skipped on import |

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

- **Phase 6** — Real-time collaboration, code review, and quality tooling.

## License

[MIT](./LICENSE)
