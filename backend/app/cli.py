import argparse

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def create_admin(login: str, password: str, display_name: str) -> None:
    if len(password) < 10:
        raise SystemExit("Password must contain at least 10 characters")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == UserRole.ADMIN)) is not None:
            raise SystemExit("An administrator already exists; create additional admins through the API")
        if db.scalar(select(User).where(User.login == login)) is not None:
            raise SystemExit("Login already exists")
        db.add(
            User(
                login=login,
                display_name=display_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                must_change_password=True,
            )
        )
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="SkillPeer21 administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-admin", help="Create the first administrator")
    create.add_argument("--login", required=True)
    create.add_argument("--password", required=True)
    create.add_argument("--display-name", required=True)
    args = parser.parse_args()

    if args.command == "create-admin":
        create_admin(args.login, args.password, args.display_name)


if __name__ == "__main__":
    main()
