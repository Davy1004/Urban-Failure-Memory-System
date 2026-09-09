"""Ingestion entry point.

    python -m app.ingestion.cli weather --city Bengaluru --start 2019-01-01
    python -m app.ingestion.cli weather-daily --city Bengaluru
    python -m app.ingestion.cli derive --city Bengaluru
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
from app.models.geography import IngestionRun, Location, WeatherCell
from app.models.derived import (
    EmergingWatch, WardAllocation, WardQuarterIndex, WatchlistSnapshot,
)
from app.models.observation import (
    Complaint, WardPeriodTotal, WeatherDaily, WeatherObservation,
)

logger = logging.getLogger("ufms.ingestion.cli")


def _date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {s!r}")


def cmd_weather(args) -> int:
    from app.ingestion.open_meteo import DEFAULT_MODEL, IFS_CELLS, load_weather

    coords = IFS_CELLS if args.model == "ecmwf_ifs" else None
    with SessionLocal() as db:
        n = load_weather(db, args.city, args.start, args.end,
                         model=args.model, coords=coords)
    print(f"{n:,} hourly rows upserted for {args.city} ({args.model})")
    return 0


def cmd_weather_daily(args) -> int:
    from app.ingestion.weather_daily import build_daily

    with SessionLocal() as db:
        n = build_daily(db, args.city)
    print(f"{n:,} daily rows upserted for {args.city}")
    return 0


def cmd_wards(args) -> int:
    import pathlib as _p
    from app.ingestion.bbmp_wards import load_hotspots, load_wards

    raw = _p.Path(args.raw_dir) if args.raw_dir else _p.Path("data/raw")
    with SessionLocal() as db:
        n_w = load_wards(db, args.city)
        n_h = load_hotspots(db, raw, args.city)
    print(f"{n_w} ward locations, {n_h} hotspot points upserted for {args.city}")
    return 0


def cmd_complaints(args) -> int:
    import pathlib as _p
    from app.ingestion.bbmp_complaints import load_complaints

    from app.ingestion.bbmp_complaints import (
        upsert_ward_period_totals, write_ward_period_totals,
    )

    raw = _p.Path(args.raw_dir) if args.raw_dir else _p.Path("data/raw")
    if args.totals:
        t = write_ward_period_totals(raw)
        with SessionLocal() as db:
            n = upsert_ward_period_totals(db, args.city, totals=t)
        print(f"{len(t):,} ward-period totals written to the CSV, "
              f"{n:,} rows upserted into ward_period_totals")
        return 0
    with SessionLocal() as db:
        rep = load_complaints(db, raw, args.city)
    t = write_ward_period_totals(raw)
    with SessionLocal() as db:
        upsert_ward_period_totals(db, args.city, totals=t)
    print(f"{rep['rows_kept']:,} complaints upserted of {rep['rows_read']:,} read")
    print(f"  by hazard   : {rep['by_code']}")
    print(f"  by severity : {rep['by_severity']}")
    print(f"  dropped     : {rep['dropped_not_hazard']:,} non-hazard, "
          f"{rep['dropped_null_ward']:,} null ward, "
          f"{rep['dropped_unresolved_ward']:,} unresolved ward, "
          f"{rep['dropped_bad_date']:,} bad date")
    return 0


def cmd_derive(args) -> int:
    """Rebuild the four derived tables the dashboard reads.

    Not an endpoint: this walks 237,157 complaints and 49,915 work orders, and
    a dashboard should not be able to trigger it. Idempotent, like every loader.
    """
    from app.derived import build_all
    from app.derived.index import build_index

    if args.index_only:
        with SessionLocal() as db:
            n = build_index(db, args.city)
        print(f"{n:,} ward-quarter rows upserted into ward_quarter_index")
        return 0
    with SessionLocal() as db:
        counts = build_all(db, args.city, args.raw_dir)
    for table, n in counts.items():
        print(f"{table:<20}: {n:>6,}")
    return 0


def cmd_status(args) -> int:
    with SessionLocal() as db:
        obs = db.execute(select(func.count()).select_from(WeatherObservation)).scalar()
        daily = db.execute(select(func.count()).select_from(WeatherDaily)).scalar()
        span = db.execute(
            select(func.min(WeatherDaily.obs_date), func.max(WeatherDaily.obs_date))
        ).one()
        locs = db.execute(select(func.count()).select_from(Location)).scalar()
        comp = db.execute(select(func.count()).select_from(Complaint)).scalar()
        wpt = db.execute(select(func.count()).select_from(WardPeriodTotal)).scalar()
        wqi = db.execute(select(func.count()).select_from(WardQuarterIndex)).scalar()
        emg = db.execute(select(func.count()).select_from(EmergingWatch)).scalar()
        alc = db.execute(select(func.count()).select_from(WardAllocation)).scalar()
        wls = db.execute(select(func.count()).select_from(WatchlistSnapshot)).scalar()
        cells = db.execute(
            select(WeatherCell.model, func.count()).group_by(WeatherCell.model)
        ).all()
        print(f"locations            : {locs:>9,}")
        print(f"complaints           : {comp:>9,}")
        print(f"ward_period_totals   : {wpt:>9,}   the index denominator")
        print(f"ward_quarter_index   : {wqi:>9,}   the relative flooding index")
        print(f"watchlist_snapshots  : {wls:>9,}")
        print(f"emerging_watch       : {emg:>9,}")
        print(f"ward_allocation      : {alc:>9,}")
        print(f"weather_observations : {obs:>9,}")
        print(f"weather_daily        : {daily:>9,}   {span[0]} .. {span[1]}")
        print(f"weather_cells        : {sum(n for _, n in cells):>9,}   "
              + ", ".join(f"{m.value} {n}" for m, n in cells))
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
    w.add_argument("--model", default="ecmwf_ifs",
                   choices=["era5", "ecmwf_ifs", "era5_land"])
    w.set_defaults(fn=cmd_weather)

    d = sub.add_parser("weather-daily", help="aggregate hourly into weather_daily")
    d.add_argument("--city", required=True)
    d.set_defaults(fn=cmd_weather_daily)

    wd = sub.add_parser("wards", help="load ward centroids + register hotspots")
    wd.add_argument("--city", default="Bengaluru")
    wd.add_argument("--raw-dir", dest="raw_dir", default=None)
    wd.set_defaults(fn=cmd_wards)

    c = sub.add_parser("complaints", help="load BBMP grievances")
    c.add_argument("--city", default="Bengaluru")
    c.add_argument("--raw-dir", dest="raw_dir", default=None)
    c.add_argument("--totals", action="store_true",
                   help="only regenerate the ward_period_totals CSV and table")
    c.set_defaults(fn=cmd_complaints)

    dv = sub.add_parser("derive", help="rebuild the four derived dashboard tables")
    dv.add_argument("--city", default="Bengaluru")
    dv.add_argument("--raw-dir", dest="raw_dir", default=None)
    dv.add_argument("--index-only", action="store_true",
                    help="only rebuild ward_quarter_index, which the other three read")
    dv.set_defaults(fn=cmd_derive)

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
