# SkillPeer21

Peer-to-peer skill exchange platform for School 21.

## Product idea

SkillPeer21 helps School 21 community members share skills and organize peer-learning sessions. Each member can list skills they can teach and skills they want to learn. The platform surfaces matches and lets members create events around those skills.

The first version is intentionally small: users are created by an administrator, any member may add skills to the shared catalogue, duplicate skills can be merged by an administrator, events can be proposed by any member, participants vote on suggested time slots, Telegram contact visibility is controlled by the user, and completed sessions may receive kudos.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Database: PostgreSQL
- ORM/migrations: SQLAlchemy 2 + Alembic
- Authentication: JWT access/refresh tokens + Argon2 password hashing
- Infrastructure: Docker Compose
- Tests: pytest

## Repository structure

```text
skillpeer21/
├── backend/
├── frontend/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Local development

Copy the environment template and start the stack:

```bash
cp .env.example .env
docker compose up --build -d
```

Apply database migrations:

```bash
docker compose exec backend alembic upgrade head
```

Create the first administrator. This bootstrap command intentionally stops working after an admin already exists; additional administrators can then be created through the API.

```bash
docker compose exec backend python -m app.cli create-admin \
  --login admin \
  --display-name "Administrator" \
  --password "replace-with-a-strong-password"
```

After startup:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Authentication and user management

Public registration does not exist. Administrators create all accounts and assign a temporary password. A new account has `must_change_password=true` until the member changes it. Password changes increment the user's token version, invalidating previously issued access and refresh tokens.

Current API endpoints:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- `POST /api/v1/users` — admin only
- `GET /api/v1/users` — admin only

Telegram username is optional. If supplied, the member chooses whether it is visible to everyone in the community or only to administrators.

## Skills

Skills are stored in a shared catalogue. Any authenticated member can create a skill and then attach it to their profile as either `teach` or `learn`. Skill names are whitespace-normalized and case-insensitive for duplicate detection.

An administrator can merge two semantically duplicate skills. During the merge, every current reference to the source skill is moved to the retained target skill. If the same user already has the target skill with the same intent, the duplicate link is removed. The source skill is deleted only after its references have been resolved.

Skill API endpoints:

- `GET /api/v1/skills`
- `POST /api/v1/skills`
- `GET /api/v1/skills/me`
- `POST /api/v1/skills/{skill_id}/links`
- `DELETE /api/v1/skills/{skill_id}/links/{intent}`
- `POST /api/v1/skills/{source_skill_id}/merge` — admin only

## MVP scope

- admin-managed users;
- authentication;
- member profile;
- community-managed skill catalogue with admin merge support;
- unlimited `teach` and `learn` skills per member;
- skill matching;
- event proposals initiated by teachers or learners;
- event time options and participant voting;
- optional Telegram username with `everyone` or `admin_only` visibility;
- community statistics for admins;
- kudos after completed sessions.

## Development workflow

Feature work is developed in branches and merged through pull requests. `main` should remain deployable.
