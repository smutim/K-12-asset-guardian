"""
Compatibility module.

Some parts of the codebase import Base from `app.db`.
The actual SQLAlchemy setup lives in `app.database`.

This file re-exports the expected objects so imports work.
"""

from .database import Base, engine, SessionLocal  # noqa: F401
