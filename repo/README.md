# TrailForge

TrailForge is a full-stack itinerary and travel-operations platform. It is designed for org-scoped planning, governance, auditability, and offline-friendly data transfer workflows.

## Architecture & Tech Stack

- Frontend: Vue 3, TypeScript, Vite, Pinia, Vue Router
- Backend: Python 3, FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL 16
- Containerization: Docker and Docker Compose

## Project Structure

Below is the current project structure in this repository.

```text
.
├── backend/                # Backend source, migrations, and Dockerfile
├── frontend/               # Frontend source, tests, and Dockerfile
├── ops/                    # Operational docs and helper assets
├── .env.example            # Not used in this repo (runtime secrets are generated)
├── docker-compose.yml      # Multi-container orchestration
├── run_tests.sh            # Standardized test execution script
└── README.md               # Project documentation
```

## Prerequisites

To ensure a consistent environment, this project runs entirely in containers. Install:

- Docker
- Docker Compose

## Running the Application

Build and start containers in detached mode:

```bash
docker-compose up --build -d
```

Environment file note:

```bash
cp .env.example .env
```

This step is **not required** for this repository because `.env.example` is intentionally not committed. Runtime secrets and most runtime config are provisioned by Docker Compose services/volumes.

Access the app:

- Frontend: `https://localhost:5173`
- Backend API: `https://localhost:8443/api`
- API Documentation: `https://localhost:8443/docs`

Stop the application:

```bash
docker-compose down -v
```

## Testing

All unit, integration, and E2E tests run via a single script:

```bash
chmod +x run_tests.sh
./run_tests.sh
```

`run_tests.sh` returns a standard exit code (`0` success, non-zero failure), which is suitable for CI/CD validation.

## Seeded Credentials

The app provisions deterministic demo users on startup for local verification only.

| Role | Email | Password | Notes |
|---|---|---|---|
| Admin | `demo-admin` | `TrailForgeDemo!123` | ORG_ADMIN role with full module access in `default-org`. |
| User | `demo-planner` | `TrailForgeDemo!123` | PLANNER role with planning and messaging permissions. |
| Read-Only | `demo-auditor` | `TrailForgeDemo!123` | AUDITOR role with read-only audit/lineage visibility. |

Note: Login uses `org_slug + username + password` (not email-based login). Default org slug: `default-org`.
