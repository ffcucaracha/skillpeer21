from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models.skill import Skill, SkillIntent, UserSkill
from app.schemas.skill import (
    SkillCreate,
    SkillMergeRequest,
    SkillRead,
    UserSkillCreate,
    UserSkillRead,
)
from app.services.skills import merge_skills, normalize_skill_name

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillRead])
def list_skills(
    _: CurrentUser,
    db: DbSession,
    q: str | None = Query(default=None, max_length=120),
) -> list[Skill]:
    stmt = select(Skill).order_by(Skill.name, Skill.id)
    if q:
        stmt = stmt.where(Skill.normalized_name.contains(normalize_skill_name(q)))
    return list(db.scalars(stmt).all())


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: SkillCreate, user: CurrentUser, db: DbSession) -> Skill:
    name = " ".join(payload.name.strip().split())
    skill = Skill(
        name=name,
        normalized_name=normalize_skill_name(name),
        created_by_user_id=user.id,
    )
    db.add(skill)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Skill with this name already exists",
        ) from exc
    db.refresh(skill)
    return skill


@router.get("/me", response_model=list[UserSkillRead])
def list_my_skills(user: CurrentUser, db: DbSession) -> list[UserSkillRead]:
    rows = db.execute(
        select(UserSkill, Skill.name)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.user_id == user.id)
        .order_by(UserSkill.intent, Skill.name)
    ).all()
    return [
        UserSkillRead(id=link.id, skill_id=link.skill_id, skill_name=name, intent=link.intent)
        for link, name in rows
    ]


@router.post("/{skill_id}/links", response_model=UserSkillRead, status_code=status.HTTP_201_CREATED)
def add_my_skill(
    skill_id: int,
    payload: UserSkillCreate,
    user: CurrentUser,
    db: DbSession,
) -> UserSkillRead:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    link = UserSkill(user_id=user.id, skill_id=skill.id, intent=payload.intent)
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Skill is already linked with this intent",
        ) from exc
    db.refresh(link)
    return UserSkillRead(id=link.id, skill_id=skill.id, skill_name=skill.name, intent=link.intent)


@router.delete("/{skill_id}/links/{intent}", status_code=status.HTTP_204_NO_CONTENT)
def remove_my_skill(
    skill_id: int,
    intent: SkillIntent,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    link = db.scalar(
        select(UserSkill).where(
            UserSkill.user_id == user.id,
            UserSkill.skill_id == skill_id,
            UserSkill.intent == intent,
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill link not found")
    db.delete(link)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{source_skill_id}/merge", response_model=SkillRead)
def merge_skill(
    source_skill_id: int,
    payload: SkillMergeRequest,
    _: AdminUser,
    db: DbSession,
) -> Skill:
    source = db.get(Skill, source_skill_id)
    target = db.get(Skill, payload.target_skill_id)
    if source is None or target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if source.id == target.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source and target skills must be different",
        )
    return merge_skills(db, source, target)
