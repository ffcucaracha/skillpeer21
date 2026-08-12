from pydantic import BaseModel, ConfigDict, Field

from app.models.skill import SkillIntent


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserSkillCreate(BaseModel):
    intent: SkillIntent


class UserSkillRead(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    intent: SkillIntent


class SkillMergeRequest(BaseModel):
    target_skill_id: int
