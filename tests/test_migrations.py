"""Do the migrations and ufms_schema.sql still describe the same database?

`ufms_schema.sql` is the canonical DDL and the file a human reads. The Alembic
chain is what actually builds the database on a deploy. Nothing forces them to
agree, and when the baseline was first generated they did not: 178
differences — every foreign key and half the indexes carried MySQL's
auto-generated names instead of the schema's, 23 columns had no server-side
DEFAULT, seven TIMESTAMP columns had become DATETIME, and `users.updated_at`
had quietly lost `ON UPDATE CURRENT_TIMESTAMP`.

None of that shows up in day-to-day use. It shows up the first time a later
migration says `op.drop_constraint("fk_cell_city")` against a database that
calls it `weather_cells_ibfk_1`, or the first time a row inserted by raw SQL
lands with a NULL where the DDL promised a default.

So this test builds a database each way and diffs information_schema — columns
with their types, defaults, positions and comments; indexes; foreign keys with
their referential actions; and the three views.

It needs a live MySQL and CREATE DATABASE rights, and skips without them.
"""
import os
import pathlib
import re
import uuid

import pytest
from sqlalchemy import create_engine, text

from app.core.config import settings

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_SQL = ROOT / "ufms_schema.sql"
SKIP = {"alembic_version"}


def _server_url() -> str:
    """The configured URL with the database name stripped off."""
    return re.sub(r"/[^/?]+(\?.*)?$", "/", settings.database_url)


@pytest.fixture(scope="module")
def server():
    url = _server_url()
    try:
        eng = create_engine(url + "information_schema", pool_pre_ping=True)
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:                                  # pragma: no cover
        pytest.skip(f"no reachable MySQL for the schema diff: {exc}")
    return eng


@pytest.fixture(scope="module")
def built(server):
    """One database built by `alembic upgrade head`, one by the raw DDL."""
    from alembic import command
    from alembic.config import Config

    tag = uuid.uuid4().hex[:8]
    mig, raw = f"ufms_t_mig_{tag}", f"ufms_t_raw_{tag}"
    url = _server_url()
    charset = "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    try:
        with server.connect() as c:
            for db in (mig, raw):
                c.execute(text(f"CREATE DATABASE `{db}` {charset}"))
            c.commit()
    except Exception as exc:                                  # pragma: no cover
        # The dev grant is scoped: GRANT ALL ON `ufms\_t\_%`.* TO 'ufms'@'%'.
        # Without it there is nowhere to build the two databases, so skip
        # rather than fail a clean checkout.
        pytest.skip(f"cannot create the throwaway test databases: {exc}")
    try:
        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "alembic"))
        prev = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = url + mig
        try:
            settings.__dict__["database_url"] = url + mig
            command.upgrade(cfg, "head")
        finally:
            settings.__dict__["database_url"] = prev or settings.database_url
            if prev is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = prev

        # the DDL hard-codes `USE ufms`, so point it at the throwaway database
        sql = SCHEMA_SQL.read_text(encoding="utf-8")
        sql = re.sub(r"CREATE DATABASE IF NOT EXISTS ufms\s*\n\s*CHARACTER SET"
                     r" utf8mb4\s*\n\s*COLLATE utf8mb4_0900_ai_ci;", "", sql)
        sql = sql.replace("USE ufms;", f"USE `{raw}`;")
        eng = create_engine(url + raw + "?charset=utf8mb4")
        with eng.connect() as c:
            for stmt in _statements(sql):
                c.execute(text(stmt))
            c.commit()
        yield mig, raw
    finally:
        with server.connect() as c:
            for db in (mig, raw):
                c.execute(text(f"DROP DATABASE IF EXISTS `{db}`"))
            c.commit()


def _statements(sql: str):
    """Split the DDL on statement-terminating semicolons.

    Quote-aware, because a naive `sql.split(";")` also splits inside string
    literals — and column COMMENTs are string literals that read like prose.
    The first one containing a semicolon cut a CREATE TABLE in half and the
    test failed with a syntax error pointing at valid SQL.
    """
    sql = re.sub(r"^\s*--.*$", "", sql, flags=re.M)
    buf, quote, i = [], None, 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            if ch == "\\":                 # backslash escape inside a literal
                buf.append(sql[i:i + 2])
                i += 2
                continue
            if ch == quote:
                if sql[i + 1:i + 2] == quote:   # doubled quote, still inside
                    buf.append(ch * 2)
                    i += 2
                    continue
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                yield stmt
            buf, i = [], i + 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        yield tail


def _rows(eng, sql, db):
    with eng.connect() as c:
        return c.execute(text(sql), {"db": db}).mappings().all()


COLS = """SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE,
                 COLUMN_DEFAULT, EXTRA, ORDINAL_POSITION, COLLATION_NAME,
                 COLUMN_COMMENT
          FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = :db"""
IDX = """SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME
         FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = :db"""
FKS = """SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.COLUMN_NAME,
                k.ORDINAL_POSITION, k.REFERENCED_TABLE_NAME,
                k.REFERENCED_COLUMN_NAME, c.UPDATE_RULE, c.DELETE_RULE
         FROM information_schema.KEY_COLUMN_USAGE k
         JOIN information_schema.REFERENTIAL_CONSTRAINTS c
           ON c.CONSTRAINT_SCHEMA = k.TABLE_SCHEMA
          AND c.CONSTRAINT_NAME = k.CONSTRAINT_NAME
         WHERE k.TABLE_SCHEMA = :db"""
TBL = """SELECT TABLE_NAME, TABLE_TYPE, ENGINE, TABLE_COLLATION
         FROM information_schema.TABLES WHERE TABLE_SCHEMA = :db"""
VWS = """SELECT TABLE_NAME, VIEW_DEFINITION
         FROM information_schema.VIEWS WHERE TABLE_SCHEMA = :db"""


def _norm(rows, db, skip_first_col=True):
    out = set()
    for r in rows:
        if r["TABLE_NAME"] in SKIP:
            continue
        vals = tuple((v.replace(f"`{db}`.", "") if isinstance(v, str) else v)
                     for k, v in r.items())
        out.add(vals)
    return out


@pytest.mark.parametrize("what,sql", [
    ("tables", TBL), ("columns", COLS), ("indexes", IDX),
    ("foreign keys", FKS), ("views", VWS),
], ids=["tables", "columns", "indexes", "foreign_keys", "views"])
def test_migrated_schema_matches_canonical_ddl(built, what, sql):
    mig, raw = built
    url = _server_url()
    a = _norm(_rows(create_engine(url + mig + "?charset=utf8mb4"), sql, mig), mig)
    b = _norm(_rows(create_engine(url + raw + "?charset=utf8mb4"), sql, raw), raw)
    only_mig = sorted(a - b)
    only_raw = sorted(b - a)
    assert not (only_mig or only_raw), (
        f"{what}: {len(only_mig)} only in the migrated database, "
        f"{len(only_raw)} only in ufms_schema.sql\n"
        f"  migrated-only: {only_mig[:5]}\n  ddl-only:      {only_raw[:5]}"
    )


def test_migration_chain_round_trips(built):
    """`upgrade head` -> `downgrade base` -> `upgrade head` must be clean.

    The autogenerated downgrade was not: it emitted op.drop_index() for
    indexes that back foreign keys, which MySQL refuses to drop.
    """
    from alembic import command
    from alembic.config import Config

    mig, _ = built
    url = _server_url()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    prev = settings.database_url
    os.environ["DATABASE_URL"] = url + mig
    settings.__dict__["database_url"] = url + mig
    try:
        command.downgrade(cfg, "base")
        eng = create_engine(url + mig + "?charset=utf8mb4")
        with eng.connect() as c:
            left = c.execute(text(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = :db AND TABLE_NAME <> 'alembic_version'"
            ), {"db": mig}).scalar()
        assert left == 0, f"{left} objects survived `alembic downgrade base`"
        command.upgrade(cfg, "head")
    finally:
        settings.__dict__["database_url"] = prev
        os.environ["DATABASE_URL"] = prev
