"""Declarative base. Importing app.models here gives Alembic every table."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Imported for the metadata side effect; Alembic autogenerate needs it.
from app import models  # noqa: E402,F401
