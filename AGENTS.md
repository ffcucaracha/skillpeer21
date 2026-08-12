# AGENTS.md

## Project

SkillPeer21 is a peer-to-peer skill exchange platform for the School 21 community.

## Architecture

- `frontend/`: React + TypeScript + Vite SPA.
- `backend/`: FastAPI application using SQLAlchemy 2 and PostgreSQL.
- PostgreSQL is the system of record.
- Docker Compose is the default local development environment.

## Product rules

- Users are created only by administrators; public self-registration is out of scope.
- A member may have any number of skills they can teach and want to learn.
- Skills come from a moderated catalogue; members may suggest new skills.
- Skill levels are intentionally not modeled in the MVP.
- Any member may propose an event either from a skill they can teach or one they want to learn.
- An event represents an initial session; the number of future sessions is not specified in advance.
- A teacher is required before an event can become confirmed.
- Event organizers may propose several time options; participants vote and the organizer confirms the final time.
- Telegram username is optional. If supplied, visibility is either public to community members or admin-only.
- Reviews and ratings are out of scope. Completed sessions may receive lightweight kudos.

## Backend conventions

- Keep HTTP concerns in API/router modules and business rules in service/domain modules.
- Keep persistence concerns separate from business logic.
- Use SQLAlchemy 2 typed mappings and Alembic migrations for schema changes.
- Validate request/response payloads with Pydantic models.
- Do not expose ORM entities directly from API routes.
- Add tests for business rules and permission boundaries.
- Prefer explicit enums/value objects for finite state rather than magic strings spread through the codebase.
- Never commit secrets or real credentials.

## Frontend conventions

- Use TypeScript strictly; avoid `any` unless there is a documented integration reason.
- Use TanStack Query for server state.
- Keep API access behind a small typed client layer.
- Keep page components thin; move reusable behavior into features/components/hooks.
- Design mobile-first and preserve accessible labels, focus states, and semantic HTML.

## Workflow

- Do not push feature work directly to `main`.
- Use focused feature branches and pull requests.
- Keep commits and PRs scoped to one coherent change.
- Before merging, run backend tests and frontend build/lint checks relevant to the change.
