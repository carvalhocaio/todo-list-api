# Pit Wall — Todo List API

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%2018-4169E1)
![uv](https://img.shields.io/badge/packaging-uv-de5fe9)
![pytest](https://img.shields.io/badge/tests-pytest-0a9edc)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A **FastAPI** RESTful to-do list API themed after the Formula 1 pit wall —
every task is a strategy call. Users register, log in, and manage their own
to-dos behind JWT authentication, with refresh token rotation, reuse
detection, per-client rate limiting, filtering, sorting, and pagination.
Built with SQLAlchemy 2.0 async, PostgreSQL, and Alembic.

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Quickstart](#quickstart)
- [API](#api)
- [Configuration](#configuration)
- [Development](#development)
- [Project structure](#project-structure)
- [Design notes](#design-notes)
- [Project origin](#project-origin)

---

## Features

- **User registration and login**: passwords hashed with Argon2 (via
  `pwdlib`), emails stored as case-insensitive `CITEXT` and unique.
- **JWT access tokens**: short-lived (15 min by default), signed with HS256,
  validated for `sub`, `iss`, `iat`, and `exp`.
- **Refresh token rotation**: opaque refresh tokens are single-use, stored
  only as SHA-256 digests, and grouped into families — replaying a used token
  revokes the whole family.
- **Ownership rules**: users only see their own to-dos; touching someone
  else's returns `403 Forbidden`, a missing one returns `404 Not Found`.
- **Filtering, search, sorting, and pagination**: `?completed=`, `?search=`
  (case-insensitive over title and description, `LIKE` wildcards escaped),
  `?sort=`, `?page=`, and `?limit=`.
- **Partial updates**: `PUT /todos/{id}` only changes the fields you send.
- **Rate limiting**: in-memory token bucket per client IP, answering
  `429 Too Many Requests` with a `Retry-After` header.
- **Consistent error envelopes**: every failure comes back as
  `{"message": ...}`, with field-level `errors` on validation failures.
- **Layered, testable design**: routers → services → repositories, with the
  clock injected so time-dependent logic is deterministic in tests.
- **Real database tests**: integration and end-to-end suites run against a
  throwaway PostgreSQL container via `testcontainers`.

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (for the local database and the integration/e2e tests)

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/carvalhocaio/todo-list-api.git
cd todo-list-api
```

### 2. Configure the environment

```bash
cp .env.example .env
```

Replace `JWT_SECRET_KEY` with a real secret (at least 32 characters):

```bash
openssl rand -hex 32
```

### 3. Install dependencies and git hooks

```bash
make sync
make hooks
```

### 4. Start PostgreSQL and apply migrations

```bash
make db-up
make migrate
```

### 5. Run the development server

```bash
make run
```

The API starts at `http://127.0.0.1:8000`.

- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc documentation: `http://127.0.0.1:8000/redoc`

---

## API

| Method | Path | Auth | Status | Description |
|---|---|---|---|---|
| `POST` | `/register` | — | `201 Created` | Create a user and return a token pair |
| `POST` | `/login` | — | `200 OK` | Authenticate and return a token pair |
| `POST` | `/refresh` | — | `200 OK` | Rotate a refresh token into a new pair |
| `POST` | `/todos` | Bearer | `201 Created` | Create a to-do |
| `GET` | `/todos` | Bearer | `200 OK` | List your to-dos (filtered, sorted, paginated) |
| `PUT` | `/todos/{id}` | Bearer | `200 OK` | Update a to-do (partial) |
| `DELETE` | `/todos/{id}` | Bearer | `204 No Content` | Delete a to-do |
| `GET` | `/health` | — | `200 OK` | Liveness check (not rate limited) |

### Endpoints and Examples

#### Register

```bash
curl -X POST "http://127.0.0.1:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Race Engineer",
    "email": "engineer@pitwall.dev",
    "password": "box-box-box"
  }'
```

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "3q2-7wEXAMPLEonly...",
  "token_type": "bearer"
}
```

#### Login

```bash
curl -X POST "http://127.0.0.1:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "engineer@pitwall.dev", "password": "box-box-box"}'
```

Returns the same token pair shape as `/register`.

#### Refresh

```bash
curl -X POST "http://127.0.0.1:8000/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "3q2-7wEXAMPLEonly..."}'
```

Returns a new pair. The refresh token you sent is now spent — sending it again
revokes every token descended from the same login.

#### Create a to-do

```bash
curl -X POST "http://127.0.0.1:8000/todos" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Plan the undercut",
    "description": "Box on lap 18 if the gap drops under 21 seconds."
  }'
```

```json
{
  "id": 1,
  "title": "Plan the undercut",
  "description": "Box on lap 18 if the gap drops under 21 seconds.",
  "completed": false,
  "created_at": "2026-09-23T12:00:00Z",
  "updated_at": "2026-09-23T12:00:00Z"
}
```

#### List to-dos

```bash
curl "http://127.0.0.1:8000/todos?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Pending tasks mentioning "tyre", oldest first
curl "http://127.0.0.1:8000/todos?completed=false&search=tyre&sort=created_at" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "data": [
    {
      "id": 1,
      "title": "Plan the undercut",
      "description": "Box on lap 18 if the gap drops under 21 seconds.",
      "completed": false,
      "created_at": "2026-09-23T12:00:00Z",
      "updated_at": "2026-09-23T12:00:00Z"
    }
  ],
  "page": 1,
  "limit": 10,
  "total": 1
}
```

| Query param | Default | Description |
|---|---|---|
| `page` | `1` | Page number (≥ 1) |
| `limit` | `10` | Page size (1–100) |
| `completed` | — | Filter by `true` / `false` |
| `search` | — | Case-insensitive substring over title and description (max 200 chars) |
| `sort` | `-created_at` | One of `created_at`, `updated_at`, `title`; prefix with `-` for descending |

#### Update a to-do

Only the fields present in the body are changed:

```bash
curl -X PUT "http://127.0.0.1:8000/todos/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'
```

```json
{
  "id": 1,
  "title": "Plan the undercut",
  "description": "Box on lap 18 if the gap drops under 21 seconds.",
  "completed": true,
  "created_at": "2026-09-23T12:00:00Z",
  "updated_at": "2026-09-23T12:30:00Z"
}
```

#### Delete a to-do

```bash
curl -i -X DELETE "http://127.0.0.1:8000/todos/1" \
  -H "Authorization: Bearer $TOKEN"
# HTTP/1.1 204 No Content
```

### Error Responses

| Status | When | Body |
|---|---|---|
| `401 Unauthorized` | Missing/invalid access token, bad credentials, invalid refresh token | `{"message": "Unauthorized"}` / `"Invalid credentials"` / `"Invalid refresh token"` |
| `403 Forbidden` | The to-do belongs to another user | `{"message": "Forbidden"}` |
| `404 Not Found` | The to-do does not exist | `{"message": "Not Found"}` |
| `409 Conflict` | Email already registered | `{"message": "Email already registered"}` |
| `422 Unprocessable Content` | Request validation failed | see below |
| `429 Too Many Requests` | Rate limit exhausted (with `Retry-After`) | `{"message": "Too Many Requests"}` |

Validation failures list every offending field:

```json
{
  "message": "Validation failed",
  "errors": [
    {
      "field": "title",
      "reason": "String should have at least 1 character"
    }
  ]
}
```

---

## Configuration

Settings are loaded via `pydantic-settings` from environment variables or from
a `.env` file. See [.env.example](.env.example).

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | *(required)* | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | *(required)* | Signing secret, at least 32 characters |
| `JWT_ALGORITHM` | `HS256` | One of `HS256`, `HS384`, `HS512` |
| `JWT_ISSUER` | `pit-wall` | `iss` claim issued and required on access tokens |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | `7` | Refresh token lifetime |
| `RATE_LIMIT_CAPACITY` | `20` | Bucket size — maximum burst per client |
| `RATE_LIMIT_REFILL_PER_SECOND` | `0.5` | Tokens restored per second |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `pitwall` | Used by `compose.yml` for the local database |

---

## Development

All standard development tasks are orchestrated through the `Makefile`:

```bash
make help          # List all available Makefile targets
make sync          # Install runtime and dev dependencies using uv
make run           # Start the development server with live reload
make db-up         # Start local PostgreSQL and wait until it is healthy
make db-down       # Stop local PostgreSQL
make migrate       # Apply Alembic migrations up to head
make migration MSG="describe change"  # Autogenerate a new migration
make test          # Run the full test suite (requires Docker)
make test-unit     # Run unit tests only (no Docker required)
make lint          # Check code with ruff
make lint-fix      # Automatically fix safe linting violations with ruff
make format        # Format code with ruff
make format-check  # Verify formatting with ruff without modifying files
make audit         # Audit dependencies for vulnerabilities with pip-audit
make ci            # Run full verification suite locally (lint, format, audit, test)
make hooks         # Install pre-commit git hooks
make hooks-run     # Run all pre-commit hooks over all files
make clean         # Remove caches and build artifacts
```

The test suite is split into three layers:

- `tests/unit` — security primitives and the rate limiter, no I/O.
- `tests/integration` — repositories, services, and the migrated schema
  against a real PostgreSQL container.
- `tests/e2e` — the full HTTP contract through the FastAPI app.

---

## Project structure

```
src/todo_list_api/
├── main.py                    # create_app factory, lifespan, and /health
├── core/
│   ├── clock.py               # Injectable Clock type and utc_now
│   ├── security.py            # Argon2 hasher, JWT codec, refresh token factory
│   └── settings.py            # Settings loaded from environment / .env
├── domain/
│   ├── auth.py                # TokenPair
│   ├── errors.py              # Domain exception hierarchy
│   ├── pagination.py          # PageRequest and Page[T]
│   └── todos.py               # TodoDraft, TodoPatch, TodoFilter, TodoSort
├── db/
│   ├── base.py                # Declarative base, naming convention, timestamps
│   ├── models.py              # User, Todo, RefreshToken ORM models
│   └── session.py             # Async engine and session factory
├── repositories/
│   ├── protocols.py           # Repository Protocols (the ports)
│   ├── users.py               # SQLAlchemy user repository
│   ├── todos.py               # SQLAlchemy todo repository (filter/sort/page)
│   └── refresh_tokens.py      # SQLAlchemy refresh token repository
├── services/
│   ├── auth.py                # Register, login, and refresh rotation
│   └── todos.py               # To-do use cases and ownership rules
└── api/
    ├── dependencies.py        # Sessions, services, and current user injection
    ├── errors.py              # Domain → HTTP error mapping and envelopes
    ├── middleware.py          # Rate limiting middleware
    ├── rate_limit.py          # In-memory token bucket limiter
    ├── routers/               # auth.py, todos.py
    └── schemas/               # Pydantic request/response models
migrations/                    # Alembic environment and versions
tests/                         # unit, integration, and e2e suites
```

---

## Design notes

### Layering

Requests flow `api → services → repositories → db`. Routers only translate
HTTP into domain inputs (`TodoDraft`, `TodoPatch`, `TodoFilter`) and back.
Services hold the business rules and depend on repository `Protocol`s, not on
SQLAlchemy directly. Domain errors are raised by services and mapped to HTTP
status codes in a single place (`api/errors.py`).

### Authentication

- **Access tokens** are stateless JWTs carrying the user id in `sub`. Every
  protected request decodes the token and loads the user; any failure is a
  uniform `401` with `WWW-Authenticate: Bearer`.
- **Refresh tokens** are random, opaque, and never stored in plain text —
  only their SHA-256 digest is persisted.
- **Rotation and reuse detection**: each login starts a token *family*.
  Refreshing marks the presented token as used and issues a new one in the
  same family. If a used token is ever presented again, the entire family is
  revoked, cutting off whoever stole it.
- **Timing-safe login**: when the email does not exist, the password is still
  verified against a decoy hash, so response times don't reveal which emails
  are registered.

### Ownership: 403 vs 404

A to-do that doesn't exist returns `404`; one that exists but belongs to
another user returns `403`, matching the roadmap.sh contract. Listing is
always scoped to the current user.

### Rate limiting

A token bucket per client IP lives in process memory: each request spends one
token, and tokens refill continuously at `RATE_LIMIT_REFILL_PER_SECOND` up to
`RATE_LIMIT_CAPACITY`. When empty, the API answers `429` with a `Retry-After`
computed from the refill rate. Idle buckets are swept periodically, and
`/health` plus the docs endpoints are exempt. Being in-memory, limits are
per-process — a multi-instance deployment would need a shared store such as
Redis.

### Time & determinism

Services and security primitives receive an injectable `Clock` (and the rate
limiter a monotonic clock), so token expiry and bucket refill are tested by
advancing time explicitly instead of sleeping.

### Database

- `users.email` is `CITEXT` with a unique constraint, so
  `Engineer@PitWall.dev` and `engineer@pitwall.dev` are the same account.
- `todos` has a composite index on `(owner_id, created_at)` to back the
  default listing order.
- Deleting a user cascades to their to-dos and refresh tokens.
- Constraint names follow an explicit naming convention, keeping Alembic
  autogenerate diffs stable.

---

## Project origin

Built as an implementation of the
[Todo List API](https://roadmap.sh/projects/todo-list-api)
project from [roadmap.sh](https://roadmap.sh).
