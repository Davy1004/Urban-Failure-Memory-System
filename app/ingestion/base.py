"""Shared ingestion machinery.

Two rules every loader follows:
  1. Idempotent. Re-running must not duplicate rows. The UNIQUE constraints
     in the schema are the safety net; loaders use INSERT ... ON DUPLICATE
     KEY UPDATE so a retried run is harmless.
  2. Traceable. Every run opens an ingestion_runs row and closes it with a
     status and row counts, so results are reproducible and the viva is easy.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import IngestionStatus
from app.models.geography import DataSource, IngestionRun

logger = logging.getLogger("ufms.ingestion")


class RunTracker:
    """Mutable counters a loader updates as it works."""

    def __init__(self, run: IngestionRun):
        self.run = run
        self.ingested = 0
        self.rejected = 0

    def ok(self, n: int = 1) -> None:
        self.ingested += n

    def bad(self, n: int = 1, reason: str = "") -> None:
        self.rejected += n
        if reason:
            logger.debug("rejected %d row(s): %s", n, reason)


def get_or_create_source(db: Session, name: str, url: str = "",
                         licence: str = "", description: str = "") -> DataSource:
    src = db.execute(
        select(DataSource).where(DataSource.name == name)
    ).scalar_one_or_none()
    if src is None:
        src = DataSource(name=name, url=url or None, licence=licence or None,
                         description=description or None)
        db.add(src)
        db.flush()
        logger.info("registered new data source: %s", name)
    return src


@contextmanager
def ingestion_run(db: Session, source_name: str, **source_kw) -> Iterator[RunTracker]:
    """Open an ingestion_runs row, yield a tracker, close it on the way out.

    On exception the run is marked 'failed' with the message stored, and the
    exception is re-raised — a silent partial load is worse than a loud crash.
    """
    source = get_or_create_source(db, source_name, **source_kw)
    run = IngestionRun(
        source_id=source.source_id,
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status=IngestionStatus.RUNNING,
    )
    db.add(run)
    db.commit()

    tracker = RunTracker(run)
    logger.info("ingestion run %s started for %s", run.run_id, source_name)

    try:
        yield tracker
    except Exception as exc:
        run.status = IngestionStatus.FAILED
        run.error_message = f"{type(exc).__name__}: {exc}"[:4000]
        run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.rows_ingested = tracker.ingested
        run.rows_rejected = tracker.rejected
        db.commit()
        logger.error("ingestion run %s FAILED: %s", run.run_id, exc)
        raise
    else:
        run.status = (
            IngestionStatus.PARTIAL if tracker.rejected else IngestionStatus.SUCCESS
        )
        run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.rows_ingested = tracker.ingested
        run.rows_rejected = tracker.rejected
        db.commit()
        logger.info(
            "ingestion run %s %s: %d ingested, %d rejected",
            run.run_id, run.status.value, tracker.ingested, tracker.rejected,
        )


def upsert_chunk(db: Session, table, rows: list[dict], update_cols: list[str]) -> int:
    """MySQL INSERT ... ON DUPLICATE KEY UPDATE for a batch of dicts.

    Relies on the table's UNIQUE constraint to detect duplicates, which is
    exactly why those constraints exist in the schema.
    """
    if not rows:
        return 0
    from sqlalchemy.dialects.mysql import insert as mysql_insert

    stmt = mysql_insert(table).values(rows)
    stmt = stmt.on_duplicate_key_update(
        **{c: getattr(stmt.inserted, c) for c in update_cols}
    )
    db.execute(stmt)
    return len(rows)


def resolve_city(db: Session, name: str):
    """Look up a city by name, case-insensitive. Raises with a useful message."""
    from app.models.geography import City

    city = db.execute(
        select(City).where(City.name.ilike(name.strip()))
    ).scalar_one_or_none()
    if city is None:
        known = db.execute(select(City.name)).scalars().all()
        raise ValueError(f"Unknown city {name!r}. Loaded cities: {known}")
    return city
