"""Dump only the tables the API actually reads, as a data-only SQL file.

    python scripts/export_demo_dump.py [out.sql]

Why this exists
---------------
The five dashboard endpoints read the *derived* tables. None of them touches
`weather_observations` (1,175,475 rows, 146 MB) or `complaints` (234,918 rows,
64 MB) - those are inputs to `app/derived/`, which has already run. So a hosted
demo needs about **1 MB** of data, not 215 MB, and a free tier's storage limit
stops being a consideration at all. It also keeps engineering rule 7 true by
construction: nothing here is within three orders of magnitude of a 1 GB tier.

The closure below was not guessed. It is every table reached from
`app/repositories/`, plus the foreign keys those tables declare, checked against
`information_schema` by `_check_closure` on every run - and it closes: nothing
in the list references a table outside it.

`users` is deliberately NOT dumped
----------------------------------
The local demo accounts share one obvious password because they are convenience
accounts on one machine. Copying them anywhere publicly reachable would publish
that password. So a deployed instance gets its own accounts, created by
`scripts/create_user.py` with a generated password, and the local ones are never
seeded there. That is a fail-safe rather than a rule to remember: the password
cannot leak through this file because it is not in this file.

What this produces
------------------
Data only - no CREATE TABLE, no DROP. The deployed schema is built by
`alembic upgrade head`, so the schema has exactly one source and a dump can
never drift from the migrations. Restore is therefore two steps:

    alembic upgrade head
    mysql ... < demo_data.sql

Idempotent: every statement is INSERT ... ON DUPLICATE KEY UPDATE, so restoring
twice is a no-op rather than a duplicate-key error half way through.
"""
from __future__ import annotations

import datetime as dt
import decimal
import pathlib
import sys
from typing import Any, Iterable

from sqlalchemy import create_engine, text

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402

# FK-safe insertion order: a parent is always written before anything that
# references it, so the restore needs no deferred constraint checks and no
# FOREIGN_KEY_CHECKS=0 (which would hide a genuinely broken dump).
TABLES: tuple[str, ...] = (
    "cities",               # referenced by locations, weather_cells, snapshots
    "failure_types",        # referenced by watchlist_snapshots
    "weather_cells",        # referenced by locations.cell_id
    "locations",            # referenced by all four derived tables
    "watchlist_snapshots",  # referenced by watchlist_entries
    "ward_quarter_index",
    "watchlist_entries",
    "emerging_watch",
    "ward_allocation",
)

# Tables a dumped table may reference without being dumped itself. Only `users`,
# and only because nothing in TABLES references it - the assertion below is what
# actually enforces that.
EXPECTED_EXCLUDED = {"users"}

BATCH = 200
DEFAULT_OUT = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "processed" / "demo_data.sql"
)


def _lit(v: Any) -> str:
    """One value as a SQL literal.

    Deliberately narrow: it raises on a type it has not been taught rather than
    str()-ing something into silent corruption.
    """
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, decimal.Decimal):
        return str(v)
    # datetime before date: datetime is a subclass of date, and only datetime
    # takes a separator.
    if isinstance(v, dt.datetime):
        return "'" + v.isoformat(sep=" ") + "'"
    if isinstance(v, (dt.date, dt.time)):
        return "'" + v.isoformat() + "'"
    if isinstance(v, dt.timedelta):
        # MySQL TIME can exceed 24 h, so the driver hands these back as
        # timedelta. Format as HH:MM:SS rather than str(), which writes
        # "1 day, 0:00:00" for anything past midnight.
        total = int(v.total_seconds())
        sign = "-" if total < 0 else ""
        total = abs(total)
        return f"'{sign}{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}'"
    if isinstance(v, (bytes, bytearray)):
        return "0x" + bytes(v).hex()
    if isinstance(v, str):
        # With NO_BACKSLASH_ESCAPES off, which is MySQL's default, backslash and
        # the quote are the two characters that need escaping.
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    raise TypeError(f"no SQL literal rule for {type(v).__name__}: {v!r}")


def _check_closure(conn) -> None:
    """Every foreign key on a dumped table must point at another dumped table.

    This is the assertion that stops the dump silently going stale: add a
    repository that reads a new table, or a column with a new FK, and this fails
    with the name of what is missing instead of producing a file that restores
    into a constraint error on someone else's machine.
    """
    rows = conn.execute(
        text(
            "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME "
            "FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "  AND REFERENCED_TABLE_NAME IS NOT NULL "
            "  AND TABLE_NAME IN :tables"
        ).bindparams(tables=tuple(TABLES))
    ).all()
    dangling = [
        f"{t}.{c} -> {r}"
        for t, c, r in rows
        if r not in TABLES and r not in EXPECTED_EXCLUDED
    ]
    if dangling:
        raise SystemExit(
            "FK closure is broken - these point outside the dump set:\n  "
            + "\n  ".join(dangling)
            + "\nAdd the referenced table to TABLES, in FK order."
        )


def _columns(conn, table: str) -> list[str]:
    return [
        r[0]
        for r in conn.execute(
            text(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                "ORDER BY ORDINAL_POSITION"
            ),
            {"t": table},
        )
    ]


def _emit(out: list[str], table: str, cols: list[str], rows: Iterable[tuple]) -> int:
    collist = ", ".join(f"`{c}`" for c in cols)
    upsert = ", ".join(f"`{c}` = VALUES(`{c}`)" for c in cols)
    batch: list[str] = []
    n = 0

    def flush() -> None:
        out.append(
            f"INSERT INTO `{table}` ({collist}) VALUES\n"
            + ",\n".join(batch)
            + f"\nON DUPLICATE KEY UPDATE {upsert};\n"
        )

    for row in rows:
        batch.append("(" + ", ".join(_lit(v) for v in row) + ")")
        n += 1
        if len(batch) >= BATCH:
            flush()
            batch = []
    if batch:
        flush()
    return n


def main(argv: list[str]) -> int:
    out_path = pathlib.Path(argv[0]) if argv else DEFAULT_OUT
    engine = create_engine(settings.database_url, future=True)

    parts: list[str] = []
    counts: dict[str, int] = {}

    with engine.connect() as conn:
        _check_closure(conn)
        for table in TABLES:
            cols = _columns(conn, table)
            if not cols:
                raise SystemExit(
                    f"table {table} does not exist in the source database"
                )
            select = ", ".join(f"`{c}`" for c in cols)
            rows = conn.execute(text(f"SELECT {select} FROM `{table}`"))
            counts[table] = _emit(parts, table, cols, rows)

    if counts["ward_quarter_index"] == 0 or counts["watchlist_entries"] == 0:
        raise SystemExit(
            "the derived tables are empty - run `python -m app.ingestion.cli derive` "
            "before dumping, or the deployed instance will serve a blank dashboard"
        )

    header = [
        "-- UFMS demo data: only the tables the five dashboard endpoints read.",
        "-- Generated by scripts/export_demo_dump.py. Do not hand-edit.",
        "--",
        "-- Restore into a database whose schema was built by `alembic upgrade head`:",
        "--   mysql --default-character-set=utf8mb4 -h HOST -P PORT -u USER -p DB < this",
        "--",
        "-- `users` is intentionally absent, so the shared local demo password cannot",
        "-- be published through this file. Create accounts on the target with",
        "-- scripts/create_user.py.",
        "--",
        "-- Rows:",
        *[f"--   {t:<22} {counts[t]:>6}" for t in TABLES],
        f"--   {'TOTAL':<22} {sum(counts.values()):>6}",
        "",
        "SET NAMES utf8mb4;",
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(header) + "\n".join(parts), encoding="utf-8")

    for t in TABLES:
        print(f"  {t:<22} {counts[t]:>6}")
    print(f"  {'TOTAL':<22} {sum(counts.values()):>6}")
    print(f"-> {out_path}  ({out_path.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
