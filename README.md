# Shift Roster

A production-ready web application for managing and publishing shift
schedules. Admins generate a monthly roster of employees × days and
edit each cell inline; the same roster is published to a public,
read-only viewer that requires no login.

> The app has completed **10 phases** of incremental development —
> project foundation, database models, authentication, the
> frontend refactor, employee management, monthly roster
> generation, the spreadsheet-style roster grid, inline cell
> editing, expand-to-full-page, and selection + copy + paste + bulk
> save. See the [Phase summary](#phase-summary) for details.

---

## Table of contents

- [Features](#features)
- [Folder structure](#folder-structure)
- [Tech stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Default admin credentials](#default-admin-credentials)
- [Application routes](#application-routes)
- [API endpoints](#api-endpoints)
- [Database migrations](#database-migrations)
- [Running the test suite](#running-the-test-suite)
- [Host port map](#host-port-map)
- [Useful Docker commands](#useful-docker-commands)
- [Light / dark mode](#light--dark-mode)
- [Public read-only roster](#public-read-only-roster)
- [Phase summary](#phase-summary)

---

## Features

- **Admin dashboard** — sidebar layout with Employees, Roster, and
  Settings sections, plus a global "System Ready" status bar.
- **Public homepage with current-week roster** — the landing page
  shows a 7-day window centred on today (clamped to the current
  month) so visitors see this week's schedule immediately. A
  "View Full Month Roster" button takes them to the full month view.
- **Employee management** — full CRUD against the `employees` table,
  with team assignment, soft-delete via `is_active`, and pagination.
- **Team management** — create teams from inside the Employees page;
  new teams show up immediately in the Add / Edit Employee dropdowns.
- **Authentication** — JWT-based, 8-hour expiry, bcrypt-hashed
  passwords, role-based admin guards on every mutating endpoint.
- **Monthly roster generation** — idempotent
  `POST /api/roster/{year}/{month}/generate` creates one row per
  active employee × day; leap years handled correctly.
- **Spreadsheet-style roster grid** — sticky frozen header row +
  first column, day cells coloured by shift type, weekend + today
  highlights, row + column hover, horizontal scroll-fade indicator,
  and automatic scrolling so today's column is always visible.
- **Inline cell editing (Phase 7)** — click a cell to type a shift
  code with live autocomplete, or double-click to open a searchable
  dropdown of all DB-backed shift types. Enter saves, Escape
  cancels, Tab / ⇧Tab moves between cells, ↑ / ↓ navigates the
  autocomplete.
- **Selection, copy, paste, bulk save (Phase 8)** — click a cell
  to select it; click+drag or Shift+click for a rectangular
  range; Ctrl+A selects every editable cell. Ctrl+C copies the
  range as tab/newline-separated text; Ctrl+V pastes it as a single
  bulk PATCH so 3,000 cells update in one request.
- **Expand to full page** — a single toggle button next to the
  "today"/"weekend" legend swatches grows the roster card to fill
  the viewport (position: fixed; inset: 0). Click again or press
  Escape to compress. Editing still works while expanded.
- **Public read-only viewer** — the same grid is exposed at
  `/roster` with no auth required, perfect for wall displays or
  shareable links.
- **Dark mode** — system-preference detection on first load, manual
  toggle, persisted in `localStorage`; works across the entire app
  including the editing input + dropdown + selection states.

---

## Folder structure

```
.
├── backend/                       # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/      # auth, employees, teams, shift_types,
│   │   │                          # roster, health
│   │   ├── core/                  # config, security, auth deps, logging
│   │   ├── db/                    # SQLAlchemy session, base, seed
│   │   ├── models/                # ORM: user, team, employee,
│   │   │                          #       shift_type, roster, setting
│   │   ├── schemas/               # Pydantic v2 request / response
│   │   ├── repositories/          # Data-access layer
│   │   ├── services/              # Business logic
│   │   └── main.py                # FastAPI entrypoint + lifespan seed
│   ├── alembic/versions/          # 5 migrations (see below)
│   ├── tests/                     # 135 pytest tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                      # Static assets served by nginx
│   ├── assets/
│   │   ├── css/styles.css         # Single app stylesheet
│   │   └── js/                    # app.js, home.js, login.js,
│   │                              # admin.js, employees.js,
│   │                              # roster-grid.js, roster.js,
│   │                              # public-roster.js, home-roster.js
│   └── pages/                     # HTML pages
│       ├── index.html             # /         (current week + admin login)
│       ├── login.html             # /login
│       ├── admin.html             # /admin
│       ├── employees.html         # /admin/employees
│       ├── roster.html            # /admin/roster (editable + select / copy / paste)
│       ├── public-roster.html     # /roster      (read-only)
│       └── settings.html          # /admin/settings (placeholder)
│
├── docker/
│   └── nginx/                     # nginx Dockerfile + default.conf
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Tech stack

| Layer       | Technology                                            |
|-------------|-------------------------------------------------------|
| Backend     | FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2      |
| Auth        | JWT (HS256) · bcrypt via passlib (pinned `bcrypt<4.1`)|
| Database    | PostgreSQL 16                                         |
| Frontend    | HTML · TailwindCSS (CDN) · Vanilla JavaScript        |
| Web server  | nginx (reverse proxy + static files)                  |
| Tests       | pytest + httpx FastAPI TestClient (in-memory SQLite)  |
| Deployment  | Docker Compose                                        |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/) v2+

---

## Quick start

1. **Copy the environment template**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` to override defaults (DB credentials, `SECRET_KEY`,
   CORS origins, etc.). The shipped `SECRET_KEY` placeholder is for
   reference only — generate your own for production.

2. **Build and start the stack**

   ```bash
   docker compose up --build
   ```

3. **Open the application**

   - Public homepage:   <http://localhost:7080>
     (current-week roster preview + Admin Login button)
   - Public roster:     <http://localhost:7080/roster>
   - Admin login:       <http://localhost:7080/login>
   - Admin roster:      <http://localhost:7080/admin/roster>
   - API docs:          <http://localhost:7080/api/docs>
   - Health check:      <http://localhost:7080/api/health>
   - Backend (direct):  <http://localhost:8001/docs>
   - PostgreSQL:        `localhost:5433`  (user/pass from `.env`)

   The backend container automatically runs `alembic upgrade head`
   on startup, then seeds the default admin user and 8 shift types
   (`S1` `Shift 1`, `S2` `Shift 2`, `S3` `Shift 3`, `G` `General`,
   `WO` `Week Off`, `CO` `Comp Off`, `L` `Leave`, `GH`
   `Govt Holiday`) on first launch.

---

## Default admin credentials

| Username | Password    | Role  |
|----------|-------------|-------|
| `admin`  | `admin123`  | admin |

The default admin is seeded idempotently by the app's `lifespan`
handler on every start (it is a no-op if the user already exists).
**Change the password before exposing the app to the internet.**

---

## Application routes

| Path                  | Auth     | Purpose                                       |
|-----------------------|----------|-----------------------------------------------|
| `/`                   | public   | Current-week roster preview + admin login    |
| `/roster`             | public   | Read-only monthly roster (expand to full page) |
| `/login`              | public   | Admin login form                              |
| `/admin`              | admin    | Dashboard (sidebar + status cards)            |
| `/admin/employees`    | admin    | Employee Directory (CRUD + Add Team)          |
| `/admin/roster`       | admin    | Monthly roster (generate / edit / select / copy / paste) |
| `/admin/settings`     | admin    | Placeholder (Coming Later)                    |

The admin roster page (`/admin/roster`) is where most of the action
happens — it supports all of the editing features (Phase 7) and the
selection / copy / paste / bulk-save features (Phase 8). Both
editing and selection are only active for admin users; the public
`/roster` page renders the same grid in read-only mode.

---

## API endpoints

All paths are under `/api`. Admin endpoints require a valid JWT in
`Authorization: Bearer <token>`. The `…/public` variant of the
roster endpoint is unauthenticated.

| Method | Path                                      | Auth     | Description                                  |
|--------|-------------------------------------------|----------|----------------------------------------------|
| GET    | `/api/health`                             | public   | `{"status":"ok"}` health check               |
| GET    | `/api/docs`                               | public   | Swagger UI                                   |
| GET    | `/api/redoc`                              | public   | ReDoc                                        |
| POST   | `/api/auth/login`                         | public   | Exchange username + password for a JWT       |
| POST   | `/api/auth/logout`                        | any user | Server-side logout (no-op, JWT is stateless) |
| GET    | `/api/auth/me`                            | any user | Current user profile                         |
| GET    | `/api/teams`                              | public   | List all teams                               |
| POST   | `/api/teams`                              | admin    | Create a team                                |
| GET    | `/api/shift-types`                        | public   | List all shift types (used by the grid)      |
| GET    | `/api/employees`                          | admin    | Paginated employee list (filters, search)    |
| POST   | `/api/employees`                          | admin    | Create an employee                           |
| GET    | `/api/employees/{id}`                     | admin    | Get one employee                             |
| PATCH  | `/api/employees/{id}`                     | admin    | Partial update                               |
| DELETE | `/api/employees/{id}`                     | admin    | Soft-delete (sets `is_active=false`)         |
| GET    | `/api/roster/{year}/{month}`              | admin    | Full month (meta + entries)                  |
| GET    | `/api/roster/{year}/{month}/public`       | public   | Same shape as the admin endpoint, no auth    |
| POST   | `/api/roster/{year}/{month}/generate`     | admin    | Idempotent: create rows for active employees |
| PATCH  | `/api/roster/entries/{entry_id}`          | admin    | Update a single cell (shift and/or remarks)  |
| PATCH  | `/api/roster/entries/bulk`                | admin    | Update many cells in one call (Phase 8)     |

### Roster response shape

```json
{
  "meta": {
    "year": 2026,
    "month": 7,
    "month_name": "July",
    "total_employees": 5,
    "total_days": 31,
    "total_records": 155,
    "is_generated": true
  },
  "entries": [
    {
      "id": 12,
      "employee": {
        "id": 3, "employee_code": "E001", "employee_name": "Alice",
        "designation": "Engineer", "team_id": 1, "team_name": "Bravo"
      },
      "date": "2026-07-14",
      "shift": { "id": 1, "code": "S1", "display_name": "Shift 1", "color": "blue" },
      "remarks": null
    }
  ]
}
```

`shift` is `null` for unassigned cells. 422 is returned for invalid
`year` (must be 2000–2100) or `month` (must be 1–12).

---

## Database migrations

Alembic is pre-configured. There are five migrations:

| Revision             | Phase | What it does                                              |
|----------------------|-------|-----------------------------------------------------------|
| `0001_initial_baseline` | 1     | Empty baseline that verifies the migration pipeline       |
| `a309597e7b4a`       | 2     | Adds `teams`, `employees`, `shift_types`, `roster`, `settings` |
| `a9de19cbb87b`       | 3     | Adds `users`                                              |
| `2026_06_27_1200`    | 5     | Makes `roster.shift_type_id` nullable                     |
| `2026_06_28_1200`    | 2.1   | Back-fills the `GH` shift type's `display_name` to `"Govt Holiday"` (was `"Gas Holiday"`) |

```bash
# Apply migrations (also runs automatically on container start)
docker compose exec backend alembic upgrade head

# Create a new migration after editing models
docker compose exec backend alembic revision --autogenerate -m "message"

# Roll back the last migration
docker compose exec backend alembic downgrade -1
```

---

## Running the test suite

The backend ships with **135 pytest tests** covering models,
repositories, services, and HTTP endpoints for every phase.
Tests use an in-memory SQLite database with
`PRAGMA foreign_keys=ON`, so they are fast and require no
PostgreSQL connection.

```bash
cd backend
python3 -m pytest tests/ -v
```

The test files are split by phase:

| File                                | Tests | Focus                                          |
|-------------------------------------|------:|------------------------------------------------|
| `tests/test_phase2_acceptance.py`   |   54  | Teams, employees, shift types, roster models (+ `GH` regression) |
| `tests/test_config_validators.py`   |    4  | `SECRET_KEY` validator hardening               |
| `tests/test_phase5_acceptance.py`   |   20  | Roster generation + month query API            |
| `tests/test_team_api.py`            |   14  | Team CRUD service + API                        |
| `tests/test_phase7_acceptance.py`   |   27  | Cell editing (PATCH) + public read-only API    |
| `tests/test_phase8_acceptance.py`   |   16  | Bulk PATCH (selection, copy, paste, performance) |

> **Note on local Python:** the project supports Python 3.9 locally
> (the Docker image uses 3.12). All type hints use `Optional[X]`
> instead of `X | None` so they parse on 3.9 — even in Pydantic
> v2 schemas, where `from __future__ import annotations` does not
> help at runtime.

---

## Host port map

| Service   | Container port | Host port | Notes                              |
|-----------|----------------|-----------|------------------------------------|
| nginx     | `80`           | `7080`    | Frontend + reverse proxy for `/api`|
| backend   | `8000`         | `8001`    | FastAPI (also reachable via nginx) |
| postgres  | `5432`         | `5433`    | Direct DB access from your host    |

To change any host-side port, edit the `ports:` block in
`docker-compose.yml`. Internal container ports are intentionally
left unchanged so service-to-service communication over the
`shiftroster-net` network is unaffected.

---

## Useful Docker commands

```bash
# Start in detached mode
docker compose up -d --build

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend

# Stop the stack
docker compose down

# Stop and remove the database volume (⚠️ deletes data)
docker compose down -v

# Rebuild a single service
docker compose build backend

# Open a shell in a running container
docker compose exec backend bash
```

---

## Light / dark mode

- The app detects the system colour scheme on first load.
- A manual toggle in the header switches between modes.
- The selected theme is persisted in `localStorage` and restored
  on subsequent visits — **no page refresh required**.
- The roster grid (frozen header, day cells, dropdown,
  validation-error flash) is fully themed for both modes.

---

## Public read-only roster

`/roster` is a read-only mirror of the admin's monthly roster.
No login is required; the page hits
`GET /api/roster/{year}/{month}/public` (no `Authorization`
header).

Behaviour:

- Month / year pickers work the same as the admin page.
- Cells show the same shift colours and weekend / today highlights.
- Clicking a cell does **not** open the editor — public users
  cannot mutate any data.
- If the admin has not generated the month yet, a friendly
  "Roster not generated yet" card is shown instead of an empty
  grid.
- The header has a "View Roster" link so visitors can reach this
  page from the homepage.

---

## Phase summary

| Phase | Status | What it delivered                                                                                                                       |
|-------|--------|-----------------------------------------------------------------------------------------------------------------------------------------|
| 1     | ✅     | Project foundation: FastAPI + nginx + PostgreSQL + Alembic, `GET /api/health`, dark mode, Docker Compose                              |
| 2     | ✅     | Database models (teams, employees, shift types, roster, settings), read-only APIs, 8 shift-type seed data                              |
| 3     | ✅     | Admin auth: JWT, bcrypt, login / logout, role-based admin guards on mutating endpoints                                                  |
| 3.5   | ✅     | Frontend refactor: dedicated `/login` page, admin layout with sidebar, route guards, removed login modal                              |
| 4.1   | ✅     | Employee Management: full CRUD API + Employee Directory UI                                                                              |
| 5     | ✅     | Monthly Roster generation: idempotent backend + month/year selectors, stats cards, preview table, Generate button                     |
| 6     | ✅     | Spreadsheet-style roster grid: sticky frozen header + first column, shift colours from DB, weekend/today highlights, row + column hover|
| 7     | ✅     | Editable cells: click-to-type with autocomplete, double-click searchable dropdown, keyboard nav, PATCH single cell, public read-only viewer |
| —     | ✅     | Expand to full page: single toggle button beside the today/weekend legend; fixed-inset full-viewport grid with editing still active, Escape to compress |
| 8     | ✅     | Selection + copy + paste + bulk save: click / click+drag / Shift+click range, Ctrl+A select-all, Ctrl+C / Ctrl+V, single bulk PATCH for up to 3,100 cells |

> Each phase ships with a self-contained acceptance test file that
> can be run independently; the full suite currently totals 135
> passing tests.
