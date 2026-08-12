from pydantic import BaseModel


class DashboardTeacher(BaseModel):
    id: int
    display_name: str
    telegram_username: str | None = None


class DashboardMatch(BaseModel):
    skill_id: int
    skill_name: str
    teachers: list[DashboardTeacher]
    learners_count: int


class DashboardSkillStat(BaseModel):
    skill_id: int
    skill_name: str
    teachers_count: int
    learners_count: int


class DashboardMember(BaseModel):
    id: int
    display_name: str
    telegram_username: str | None = None


class DashboardTeachingMember(DashboardMember):
    skills: list[str]


class DashboardSummary(BaseModel):
    members_count: int
    skills_count: int
    teaching_offers_count: int
    teaching_members_count: int
    learning_goals_count: int
    matched_learning_goals_count: int


class DashboardRead(BaseModel):
    summary: DashboardSummary
    matches: list[DashboardMatch]
    skills: list[DashboardSkillStat]
    members: list[DashboardMember]
    teaching_members: list[DashboardTeachingMember]
