"""Initial seed data for the application.

Idempotent helpers insert default rows **only if they are not already
present** so it is safe to invoke them on every startup.
"""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.shift_type import ShiftType
from app.models.user import User

logger = logging.getLogger(__name__)


# Default shift type catalogue.
# Each entry: (code, display_name, color, display_order)
DEFAULT_SHIFT_TYPES: List[tuple[str, str, str, int]] = [
    ("S1", "Shift 1",     "blue",    10),
    ("S2", "Shift 2",     "green",   20),
    ("S3", "Shift 3",     "purple",  30),
    ("G",  "General",     "violet",  40),
    ("WO", "Week Off",    "gray",    50),
    ("CO", "Comp Off",    "orange",  60),
    ("L",  "Leave",       "red",     70),
    ("GH", "Gas Holiday", "yellow",  80),
]

# Default admin account
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def seed_shift_types(db: Session) -> int:
    """Insert default shift types that are not yet present.

    Returns the number of rows actually inserted.
    """
    existing = set(
        db.execute(select(ShiftType.code)).scalars().all()
    )

    inserted = 0
    for code, display_name, color, display_order in DEFAULT_SHIFT_TYPES:
        if code in existing:
            continue
        db.add(
            ShiftType(
                code=code,
                display_name=display_name,
                color=color,
                display_order=display_order,
                is_active=True,
            )
        )
        inserted += 1

    if inserted:
        db.commit()
        logger.info("Seeded %d shift type(s)", inserted)
    else:
        logger.debug("Shift types already present, no seeding needed")
    return inserted


def seed_admin_user(db: Session) -> int:
    """Insert the default admin user if no admin exists.

    Returns 1 if a user was inserted, 0 otherwise.
    """
    existing = db.execute(
        select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
    ).scalars().first()

    if existing is not None:
        logger.debug("Admin user already exists, skipping seed")
        return 0

    db.add(
        User(
            username=DEFAULT_ADMIN_USERNAME,
            full_name="Administrator",
            email="admin@shiftroster.local",
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
    )
    db.commit()
    logger.info("Seeded default admin user (username=%s)", DEFAULT_ADMIN_USERNAME)
    return 1
