# AI-Assisted Workflow Builder

A visual workflow automation platform for multi-organization approval processes, with deterministic workflow execution and optional AI-assisted documentation and review.

## Planned Stack

- Backend: FastAPI, Pydantic, MongoDB, Redis, background workers, Pytest
- Frontend: React, TypeScript, React Flow, TanStack Query, React Hook Form
- Infrastructure: Docker Compose

## Core Ideas

- Visual workflows made from start, approval, condition, delay, and end nodes
- Deterministic validation before activation
- Append-only instance events for auditability
- Approval tasks with concurrency-safe decisions
- Delay handling through scheduled background jobs
- Optional AI features that explain and review workflows without executing them

## Project Structure

```text
backend/
  app/
    api/          FastAPI routes
    core/         Configuration, security, shared app setup
    db/           Database connections and persistence helpers
    domain/       Business logic modules
    engine/       Workflow execution engine and node handlers
    models/       Database models
    schemas/      API schemas
    services/     Application services
    workers/      Background workers
  tests/          Backend unit and integration tests

frontend/
  src/
    api/          API client code
    app/          App shell and providers
    components/   Shared UI components
    features/     Feature-specific frontend modules
    hooks/        Shared React hooks
    lib/          Shared utilities
    routes/       Route definitions
    styles/       Global styles
    types/        Shared TypeScript types
  tests/          Frontend and end-to-end tests

infra/
  docker/         Docker-related configuration

docs/
  architecture/  Architecture notes
  api/           API documentation

scripts/         Developer and maintenance scripts
```

## Status

Backend foundation in progress. Current backend features include authentication, organizations, workflow drafts, deterministic workflow validation, execution for start/condition/end nodes, approval tasks, delay scheduling, and a one-shot scheduler worker.

## Backend Commands

Install backend dependencies:

```powershell
cd backend
python -m pip install -e ".[dev]"
```

Run the API:

```powershell
.\scripts\run-api.ps1
```

Run backend tests:

```powershell
.\scripts\test-backend.ps1
```

Process due scheduled jobs once:

```powershell
.\scripts\run-scheduler-once.ps1
```

## Backend API Snapshot

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `POST /api/orgs`
- `GET /api/orgs`
- `GET /api/orgs/{organization_id}`
- `POST /api/orgs/{organization_id}/workflows`
- `GET /api/orgs/{organization_id}/workflows`
- `GET /api/orgs/{organization_id}/workflows/{workflow_id}`
- `PUT /api/orgs/{organization_id}/workflows/{workflow_id}`
- `DELETE /api/orgs/{organization_id}/workflows/{workflow_id}`
- `POST /api/orgs/{organization_id}/workflows/{workflow_id}/validate`
- `POST /api/orgs/{organization_id}/workflows/{workflow_id}/activate`
- `POST /api/orgs/{organization_id}/workflows/{workflow_id}/instances`
- `GET /api/orgs/{organization_id}/instances/{instance_id}`
- `GET /api/orgs/{organization_id}/instances/{instance_id}/events`
- `GET /api/orgs/{organization_id}/tasks`
- `GET /api/orgs/{organization_id}/tasks/{task_id}`
- `POST /api/orgs/{organization_id}/tasks/{task_id}/approve`
- `POST /api/orgs/{organization_id}/tasks/{task_id}/reject`
