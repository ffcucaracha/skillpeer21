from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.skill import Skill, UserSkill


def normalize_skill_name(name: str) -> str:
    return " ".join(name.strip().split()).casefold()


def merge_skills(db: Session, source: Skill, target: Skill) -> Skill:
    if source.id == target.id:
        raise ValueError("source and target skills must be different")

    source_links = list(db.scalars(select(UserSkill).where(UserSkill.skill_id == source.id)).all())
    for link in source_links:
        duplicate = db.scalar(
            select(UserSkill).where(
                UserSkill.user_id == link.user_id,
                UserSkill.skill_id == target.id,
                UserSkill.intent == link.intent,
            )
        )
        if duplicate is not None:
            db.delete(link)
        else:
            link.skill_id = target.id

    db.execute(update(Event).where(Event.skill_id == source.id).values(skill_id=target.id))
    db.delete(source)
    db.commit()
    db.refresh(target)
    return target
