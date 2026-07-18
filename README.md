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

Initial project scaffold.
