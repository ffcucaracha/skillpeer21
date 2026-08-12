from fastapi import APIRouter
from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import aliased

from app.api.deps import CurrentUser, DbSession
from app.models.skill import Skill, SkillIntent, UserSkill
from app.models.user import TelegramVisibility, User, UserRole
from app.schemas.dashboard import (
    DashboardMatch,
    DashboardMember,
    DashboardRead,
    DashboardSkillStat,
    DashboardSummary,
    DashboardTeacher,
    DashboardTeachingMember,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _visible_telegram(
    viewer: User,
    telegram_username: str | None,
    visibility: TelegramVisibility,
) -> str | None:
    if not telegram_username:
        return None
    if visibility == TelegramVisibility.EVERYONE or viewer.role == UserRole.ADMIN:
        return telegram_username
    return None


@router.get("", response_model=DashboardRead)
def get_dashboard(user: CurrentUser, db: DbSession) -> DashboardRead:
    members_count = db.scalar(
        select(func.count(User.id)).where(User.is_active.is_(True))
    ) or 0
    skills_count = db.scalar(select(func.count(Skill.id))) or 0
    teaching_offers_count = db.scalar(
        select(func.count(UserSkill.id)).where(UserSkill.intent == SkillIntent.TEACH)
    ) or 0
    teaching_members_count = db.scalar(
        select(func.count(distinct(UserSkill.user_id)))
        .join(User, User.id == UserSkill.user_id)
        .where(UserSkill.intent == SkillIntent.TEACH, User.is_active.is_(True))
    ) or 0
    learning_goals_count = db.scalar(
        select(func.count(UserSkill.id)).where(UserSkill.intent == SkillIntent.LEARN)
    ) or 0

    teacher_link = aliased(UserSkill)
    matched_learning_goals_count = db.scalar(
        select(func.count(distinct(UserSkill.id)))
        .join(
            teacher_link,
            and_(
                teacher_link.skill_id == UserSkill.skill_id,
                teacher_link.intent == SkillIntent.TEACH,
                teacher_link.user_id != UserSkill.user_id,
            ),
        )
        .join(User, User.id == teacher_link.user_id)
        .where(UserSkill.intent == SkillIntent.LEARN, User.is_active.is_(True))
    ) or 0

    skill_rows = db.execute(
        select(
            Skill.id,
            Skill.name,
            func.count(case((UserSkill.intent == SkillIntent.TEACH, 1))).label("teachers_count"),
            func.count(case((UserSkill.intent == SkillIntent.LEARN, 1))).label("learners_count"),
        )
        .outerjoin(UserSkill, UserSkill.skill_id == Skill.id)
        .group_by(Skill.id, Skill.name)
        .order_by(func.count(UserSkill.id).desc(), Skill.name)
    ).all()
    skills = [
        DashboardSkillStat(
            skill_id=skill_id,
            skill_name=name,
            teachers_count=teachers_count,
            learners_count=learners_count,
        )
        for skill_id, name, teachers_count, learners_count in skill_rows
    ]

    member_rows = db.execute(
        select(User.id, User.display_name, User.telegram_username, User.telegram_visibility)
        .where(User.is_active.is_(True))
        .order_by(User.display_name, User.id)
    ).all()
    members = [
        DashboardMember(
            id=member_id,
            display_name=display_name,
            telegram_username=_visible_telegram(user, telegram_username, telegram_visibility),
        )
        for member_id, display_name, telegram_username, telegram_visibility in member_rows
    ]

    teaching_rows = db.execute(
        select(
            User.id,
            User.display_name,
            User.telegram_username,
            User.telegram_visibility,
            Skill.name,
        )
        .join(UserSkill, UserSkill.user_id == User.id)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.intent == SkillIntent.TEACH, User.is_active.is_(True))
        .order_by(User.display_name, Skill.name)
    ).all()
    teaching_by_user: dict[int, DashboardTeachingMember] = {}
    for teacher_id, display_name, telegram_username, telegram_visibility, skill_name in teaching_rows:
        teacher = teaching_by_user.get(teacher_id)
        if teacher is None:
            teacher = DashboardTeachingMember(
                id=teacher_id,
                display_name=display_name,
                telegram_username=_visible_telegram(user, telegram_username, telegram_visibility),
                skills=[],
            )
            teaching_by_user[teacher_id] = teacher
        teacher.skills.append(skill_name)
    teaching_members = list(teaching_by_user.values())

    learning_rows = db.execute(
        select(Skill.id, Skill.name)
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .where(UserSkill.user_id == user.id, UserSkill.intent == SkillIntent.LEARN)
        .order_by(Skill.name)
    ).all()

    matches: list[DashboardMatch] = []
    for skill_id, skill_name in learning_rows:
        teacher_rows = db.execute(
            select(User.id, User.display_name, User.telegram_username, User.telegram_visibility)
            .join(UserSkill, UserSkill.user_id == User.id)
            .where(
                UserSkill.skill_id == skill_id,
                UserSkill.intent == SkillIntent.TEACH,
                User.id != user.id,
                User.is_active.is_(True),
            )
            .order_by(User.display_name, User.id)
        ).all()
        if not teacher_rows:
            continue

        learners_count = db.scalar(
            select(func.count(UserSkill.id)).where(
                UserSkill.skill_id == skill_id,
                UserSkill.intent == SkillIntent.LEARN,
            )
        ) or 0
        teachers = [
            DashboardTeacher(
                id=teacher_id,
                display_name=display_name,
                telegram_username=_visible_telegram(user, telegram_username, telegram_visibility),
            )
            for teacher_id, display_name, telegram_username, telegram_visibility in teacher_rows
        ]
        matches.append(
            DashboardMatch(
                skill_id=skill_id,
                skill_name=skill_name,
                teachers=teachers,
                learners_count=learners_count,
            )
        )

    matches.sort(key=lambda item: (-len(item.teachers), item.skill_name.casefold()))

    return DashboardRead(
        summary=DashboardSummary(
            members_count=members_count,
            skills_count=skills_count,
            teaching_offers_count=teaching_offers_count,
            teaching_members_count=teaching_members_count,
            learning_goals_count=learning_goals_count,
            matched_learning_goals_count=matched_learning_goals_count,
        ),
        matches=matches,
        skills=skills,
        members=members,
        teaching_members=teaching_members,
    )
