from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.events import router as events_router
from app.api.routes.skills import router as skills_router
from app.api.routes.users import router as users_router

app = FastAPI(
    title="SkillPeer21 API",
    version="0.5.0",
    description="Peer-to-peer skill exchange platform for School 21.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
