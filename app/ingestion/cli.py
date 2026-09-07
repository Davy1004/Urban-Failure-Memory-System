"""Ingestion entry point.

    python -m app.ingestion.cli weather --city Bengaluru --start 2019-01-01
    python -m app.ingestion.cli weather-daily --city Bengaluru
    python -m app.ingestion.cli status

Every loader is idempotent, so re-running any command is safe.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime

from sqlalchemy import func, select

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models.geography import IngestionRun
from app.models.observation import WeatherDaily, WeatherObservation

logger = logging.getLogger("ufms.ingestion.cli")


def _date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {s!r}")


def cmd_weather(args) -> int:
    from app.ingestion.open_meteo import load_weather

    with SessionLocal() as db:
        n = load_weather(db, args.city, args.start, args.end)
    print(f"{n:,} hourly rows upserted for {args.city}")
    return 0


def cmd_weather_daily(args) -> int:
    from app.ingestion.weather_daily import build_daily

    with SessionLocal() as db:
        n = build_daily(db, args.city)
    print(f"{n:,} daily rows upserted for {args.city}")
    return 0


def cmd_status(args) -> int:
    with SessionLocal() as db:
        obs = db.execute(select(func.count()).select_from(WeatherObservation)).scalar()
        daily = db.execute(select(func.count()).select_from(WeatherDaily)).scalar()
        span = db.execute(
            select(func.min(WeatherDaily.obs_date), func.max(WeatherDaily.obs_date))
        ).one()
        print(f"weather_observations : {obs:>9,}")
        print(f"weather_daily        : {daily:>9,}   {span[0]} .. {span[1]}")
        print("\nrecent ingestion runs:")
        runs = db.execute(
            select(IngestionRun).order_by(IngestionRun.run_id.desc()).limit(8)
        ).scalars().all()
        for r in runs:
            print(f"  #{r.run_id:<4} {r.status.value:<8} "
                  f"in={r.rows_ingested or 0:>8,} bad={r.rows_rejected or 0:>5,} "
                  f"{r.started_at}")
    return 0


def main(argv=None) -> int:
    configure_logging()
    p = argparse.ArgumentParser(prog="python -m app.ingestion.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("weather", help="fetch hourly ERA5 from Open-Meteo")
    w.add_argument("--city", required=True)
    w.add_argument("--start", type=_date, required=True)
    w.add_argument("--end", type=_date, default=None)
    w.set_defaults(fn=cmd_weather)

    d = sub.add_parser("weather-daily", help="aggregate hourly into weather_daily")
    d.add_argument("--city", required=True)
    d.set_defaults(fn=cmd_weather_daily)

    s = sub.add_parser("status", help="row counts and recent runs")
    s.set_defaults(fn=cmd_status)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except Exception as exc:
        logger.error("%s failed: %s", args.cmd, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
