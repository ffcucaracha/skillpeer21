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
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .env.prod.example
└── README.md
```

## Local development

Requirements: Docker with Docker Compose plugin.

Copy the environment template:

```bash
cp .env.example .env
```

Start the development stack with hot reload for FastAPI and Vite:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

In another terminal apply database migrations:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend alembic upgrade head
```

Create the first administrator. The bootstrap command stops working after an administrator already exists; additional users and administrators are created from the admin interface.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m app.cli create-admin \
  --login admin \
  --display-name "Administrator" \
  --password "replace-with-a-strong-password"
```

After startup:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Source directories are bind-mounted into the development containers. Changes under `backend/` restart Uvicorn automatically; changes under `frontend/` are picked up by Vite HMR.

Stop the stack with:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

To also remove the local PostgreSQL volume and reset the database:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

## Production Docker

Copy the production environment template and replace all placeholder secrets:

```bash
cp .env.prod.example .env.prod
```

Start the production stack:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

The production stack builds the React application once and serves it through nginx. nginx proxies `/api/*` to FastAPI, PostgreSQL is not published to the host, FastAPI runs without reload, and Alembic migrations are applied automatically before the backend starts.

The service is available on `http://localhost` by default. Change `HTTP_PORT` in `.env.prod` when port 80 is unavailable.

Create the first administrator after the first deployment:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend python -m app.cli create-admin \
  --login admin \
  --display-name "Administrator" \
  --password "replace-with-a-strong-password"
```

View logs or stop the stack:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f

docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

TLS/HTTPS should normally be terminated by an external reverse proxy or load balancer in front of this Compose stack.

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
