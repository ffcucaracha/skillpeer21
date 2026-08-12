# SkillPeer21

Peer-to-peer skill exchange platform for School 21.

## Product idea

SkillPeer21 helps School 21 community members share skills and organize peer-learning sessions. Each member can list skills they can teach and skills they want to learn. The platform surfaces matches and lets members create events around those skills.

The first version is intentionally small: users are created by an administrator, skills are moderated, events can be proposed by any member, participants vote on suggested time slots, Telegram contact visibility is controlled by the user, and completed sessions may receive kudos.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Database: PostgreSQL
- ORM/migrations: SQLAlchemy 2 + Alembic
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

Copy the environment template:

```bash
cp .env.example .env
```

Start the stack:

```bash
docker compose up --build
```

After startup:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## MVP scope

The planned first milestone includes:

- admin-managed users;
- authentication;
- member profile;
- moderated skill catalogue;
- unlimited `can teach` and `want to learn` skills per member;
- skill matching;
- event proposals initiated by teachers or learners;
- event time options and participant voting;
- optional Telegram username with `public` or `admin only` visibility;
- community statistics for admins;
- kudos after completed sessions.

## Development workflow

Feature work is developed in branches and merged through pull requests. `main` should remain deployable.
