"""Create (or reset the password of) a UFMS account.

    python scripts/create_user.py --email demo.officer@ufms-demo.org \
        --name "Demo Officer" --role officer

Prints a generated password once and never stores it anywhere but the database,
as a bcrypt hash. Pass `--password` to set a specific one instead, which is
what the local convenience accounts use.

Why this is a script and not a snippet in the README
---------------------------------------------------
`/auth/register` is admin-only, so the first account has to be made directly
against the database, and the README's inline `python - <<PY` snippet was the
only way to do it. That snippet also had a hard-coded password in it, which is
exactly the thing that must not be copied onto anything publicly reachable.

`scripts/export_demo_dump.py` deliberately excludes the `users` table for the
same reason: a hosted instance gets its own accounts, made here, with generated
passwords. The local demo accounts and their shared password never leave this
machine.

Against a hosted database, point DATABASE_URL at it for the one command:

    DATABASE_URL='mysql+pymysql://USER:PW@HOST:PORT/DB?ssl_ca=...' \
        python scripts/create_user.py --email officer@... --role officer
"""
from __future__ import annotations

import argparse
import pathlib
import secrets
import string
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402

# No lookalikes: O/0 and l/1/I are read off a slide or a sticky note and typed
# wrong, and a password that has to be dictated during a demo is not the place
# to be clever.
ALPHABET = (
    "".join(c for c in string.ascii_letters if c not in "lIO")
    + "".join(c for c in string.digits if c not in "01")
    + "-_.+"
)


def generate(length: int = 20) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--email", required=True)
    ap.add_argument("--name")
    ap.add_argument("--role", choices=[r.value for r in UserRole], default="officer")
    ap.add_argument("--department")
    ap.add_argument(
        "--password",
        help="set this password instead of generating one; it is echoed back, "
        "so do not use this for anything publicly reachable",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="the email already exists: set a new password on it rather than failing",
    )
    args = ap.parse_args()

    email = args.email.strip().lower()
    password = args.password or generate()
    generated = args.password is None

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            if not args.reset:
                print(
                    f"{email} already exists (user_id {existing.user_id}, "
                    f"role {existing.role.value}).\n"
                    "Pass --reset to set a new password on it.",
                    file=sys.stderr,
                )
                return 1
            existing.password_hash = hash_password(password)
            existing.is_active = True
            db.commit()
            action = "password reset for"
            user_id = existing.user_id
        else:
            user = User(
                name=args.name or email.split("@")[0],
                email=email,
                password_hash=hash_password(password),
                role=UserRole(args.role),
                department=args.department,
                is_active=True,
            )
            db.add(user)
            db.commit()
            action = "created"
            user_id = user.user_id
    finally:
        db.close()

    print(f"{action} {email}  (user_id {user_id}, role {args.role})")
    print(f"password: {password}")
    if generated:
        print(
            "\nThis is the only time it is shown - it is stored as a bcrypt hash.\n"
            "Record it somewhere before closing this terminal."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
