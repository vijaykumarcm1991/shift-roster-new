# ===========================================================
# Shift Roster
# ===========================================================

A production-ready foundation for the **Shift Roster** application.

This repository contains **Phase 1** of the project: a clean, scalable
foundation with a FastAPI backend, a vanilla-JS / Tailwind frontend,
PostgreSQL, Alembic migrations, nginx reverse proxy, and a fully
containerised Docker Compose setup.

> Future phases will add employee management, authentication, roster
> generation, and shift assignment on top of this foundation.

---

## Folder structure

```
.
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/              # Routers
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   ├── core/             # Settings, logging, config
│   │   ├── db/               # SQLAlchemy session & base
│   │   ├── models/           # ORM models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic (placeholder)
│   │   ├── static/           # Static assets served by backend
│   │   ├── templates/        # Jinja2 templates (served by nginx in prod)
│   │   ├── utils/            # Helpers
│   │   └── main.py           # FastAPI entrypoint
│   ├── alembic/              # Database migrations
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                 # Static assets served by nginx
│   ├── index.html
│   ├── css/
│   └── js/
│
├── docker/
│   └── nginx/                # nginx Dockerfile & config
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Tech stack

| Layer       | Technology                              |
|-------------|------------------------------------------|
| Backend     | FastAPI · SQLAlchemy · Alembic · Pydantic v2 |
| Database    | PostgreSQL 16                            |
| Frontend    | HTML · TailwindCSS · Vanilla JavaScript  |
| Web server  | nginx                                    |
| Deployment  | Docker Compose                           |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/) v2+

---

## Quick start

1. **Copy environment template**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` to override defaults (DB credentials, secret key, etc.).

2. **Build and start the stack**

   ```bash
   docker compose up --build
   ```

3. **Open the application**

   - Frontend (nginx):    <http://localhost:7080>
   - Backend API docs:    <http://localhost:7080/api/docs>
   - Health check:        <http://localhost:7080/api/health>
   - Backend (direct):    <http://localhost:8001/docs>
   - PostgreSQL (direct): `localhost:5433`  (user/pass from `.env`)

The backend container automatically runs `alembic upgrade head` on
startup so migrations are always applied.

---

## Host port map

| Service   | Container port | Host port | Notes                              |
|-----------|----------------|-----------|------------------------------------|
| nginx     | `80`           | `7080`    | Frontend + reverse proxy for `/api`|
| backend   | `8000`         | `8001`    | FastAPI (also reachable via nginx) |
| postgres  | `5432`         | `5433`    | Direct DB access from your host    |

To change any of the host-side ports, edit the `ports:` block in
`docker-compose.yml`. The internal container ports are intentionally
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

# Run an arbitrary command inside a service
docker compose exec backend bash
```

---

## Database migrations

Alembic is pre-configured. The initial migration (the empty baseline
that verifies the migration pipeline works) is part of Phase 1.

```bash
# Apply migrations (also runs automatically on container start)
docker compose exec backend alembic upgrade head

# Create a new migration after adding models
docker compose exec backend alembic revision --autogenerate -m "message"

# Roll back the last migration
docker compose exec backend alembic downgrade -1
```

---

## API endpoints (Phase 1)

| Method | Path           | Description           |
|--------|----------------|-----------------------|
| GET    | `/api/health`  | Health-check endpoint |
| GET    | `/api/docs`    | Swagger UI            |
| GET    | `/api/redoc`   | ReDoc                 |

Example:

```bash
# via nginx (recommended)
curl http://localhost:7080/api/health
# {"status":"ok"}

# or directly against the backend
curl http://localhost:8001/api/health
# {"status":"ok"}
```

---

## Light / Dark mode

- The dashboard detects the system theme on first load.
- A manual toggle in the header switches between modes.
- The selected theme is persisted in `localStorage` and is restored
  on subsequent visits — **no page refresh required**.

---

## Phase 1 acceptance criteria

- [x] `docker compose up` starts the stack
- [x] Homepage is served by nginx
- [x] Light mode works
- [x] Dark mode works
- [x] Theme preference persists across reloads
- [x] `GET /api/health` returns `{"status":"ok"}`
- [x] PostgreSQL is reachable from the backend
- [x] Alembic migrations apply cleanly
- [x] Responsive layout on mobile, tablet, and desktop
- [x] Clean, scalable folder structure
