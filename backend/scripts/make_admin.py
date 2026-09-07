"""Create or promote a CricNetra admin.

Admins can't self-register (sign-up rejects the admin role), so the very first
admin — who approves everyone else's elevated-role requests — is minted here.

Usage (from the backend/ directory, with CRICNETRA_DATABASE_URL set):

    # promote an existing user (by username or mobile) to admin
    python -m scripts.make_admin <username-or-mobile>

    # create a brand-new admin
    python -m scripts.make_admin --create -u admin -n "Site Admin" -m 9990001111 -p "secret123"

    # list current admins
    python -m scripts.make_admin --list
"""

from __future__ import annotations

import argparse
import sys

from app.core.security import hash_password
from app.repositories.user_repository import UserRepository


def promote(repo: UserRepository, identifier: str) -> tuple[bool, str]:
    user = repo.get_by_identifier(identifier)
    if user is None:
        return False, f"No user found for '{identifier}'."
    if user.role == "admin":
        return True, f"{user.username} is already an admin ({user.role_code})."
    updated = repo.set_role(user.id, "admin")
    return True, f"Promoted {updated.username} to admin ({updated.role_code})."


def create(repo: UserRepository, full_name: str, username: str, mobile_no: str, password: str) -> tuple[bool, str]:
    if repo.get_by_username(username) is not None:
        return False, f"Username '{username}' is already taken."
    if repo.get_by_mobile(mobile_no) is not None:
        return False, f"Mobile '{mobile_no}' is already registered."
    u = repo.add_user(
        full_name=full_name, username=username, mobile_no=mobile_no,
        password_hash=hash_password(password), role="admin",
    )
    return True, f"Created admin {u.username} ({u.user_code} · {u.role_code})."


def _repo() -> UserRepository:
    from app.core.config import settings

    if not settings.database_url:
        raise SystemExit("CRICNETRA_DATABASE_URL is not set — point it at your database first.")
    from app.db.session import get_sessionmaker, init_db
    from app.repositories.sql_user_repository import SqlUserRepository

    init_db()
    return SqlUserRepository(get_sessionmaker())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="make_admin", description="Create or promote a CricNetra admin.")
    p.add_argument("identifier", nargs="?", help="username or mobile of an existing user to promote")
    p.add_argument("--create", action="store_true", help="create a new admin instead of promoting")
    p.add_argument("-u", "--username")
    p.add_argument("-n", "--name")
    p.add_argument("-m", "--mobile")
    p.add_argument("-p", "--password")
    p.add_argument("--list", action="store_true", help="list current admins and exit")
    args = p.parse_args(argv)

    repo = _repo()

    if args.list:
        admins = repo.list_users("admin")
        if not admins:
            print("No admins yet.")
        for a in admins:
            print(f"  {a.username}  -  {a.role_code}  -  {a.full_name}")
        return 0

    if args.create:
        missing = [flag for flag, val in
                   (("--username", args.username), ("--name", args.name),
                    ("--mobile", args.mobile), ("--password", args.password)) if not val]
        if missing:
            raise SystemExit("Creating an admin needs: " + ", ".join(missing))
        ok, msg = create(repo, args.name, args.username.strip().lower(), args.mobile.strip(), args.password)
    elif args.identifier:
        ok, msg = promote(repo, args.identifier.strip().lower())
    else:
        p.print_help()
        return 0

    print(("OK - " if ok else "FAILED - ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
