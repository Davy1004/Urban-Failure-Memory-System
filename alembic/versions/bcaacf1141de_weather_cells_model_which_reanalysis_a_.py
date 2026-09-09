"""weather_cells.model: which reanalysis a cell belongs to

Two reanalyses are in play (profile §17). ERA5 at ~25 km resolves BBMP into
3 distinct cells; ECMWF-IFS at ~9 km resolves it into 14. Both sets live in
`weather_cells` — 1-9 are ERA5, 10-23 are IFS — and until now which was which
was recorded nowhere but a sentence in CLAUDE.md.

Two cells from different models at the same coordinate are DIFFERENT cells,
so `model` joins the unique key rather than sitting beside it as a label.

Revision ID: bcaacf1141de
Revises: d592327e5d7c
Create Date: 2026-09-08 21:54:44.049931
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bcaacf1141de'
down_revision: Union[str, None] = 'd592327e5d7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The 14 native ECMWF-IFS grid points the 198 ward centroids snap to. Copied
# literally rather than imported from app.ingestion.open_meteo: a migration
# has to keep meaning what it meant on the day it ran, and application
# constants move.
IFS_CELLS = [
    (12.829530, 77.586210),
    (12.899820, 77.493190), (12.899820, 77.574930), (12.899820, 77.656670),
    (12.970120, 77.481810), (12.970120, 77.563640), (12.970120, 77.645450),
    (12.970120, 77.727270),
    (13.040420, 77.470430), (13.040420, 77.552320), (13.040420, 77.634220),
    (13.040420, 77.716110),
    (13.110720, 77.540990), (13.110720, 77.622950),
]


def upgrade() -> None:
    # op.add_column() cannot place a column, and ufms_schema.sql declares
    # `model` between city_id and latitude. Keeping the ordinal positions
    # aligned is what lets tests/test_migrations.py compare the two schemas
    # column for column.
    op.execute(
        "ALTER TABLE weather_cells "
        "ADD COLUMN model ENUM('era5','ecmwf_ifs','era5_land') "
        "NOT NULL DEFAULT 'era5' "
        "COMMENT 'which reanalysis this cell belongs to' "
        "AFTER city_id"
    )

    # Backfill before the constraint changes. Defaulting every existing row to
    # 'era5' would silently mislabel the 14 IFS cells that currently carry the
    # entire pipeline, so name them explicitly. On a fresh database this
    # matches nothing and is a no-op.
    pairs = ", ".join(f"({lat:.6f}, {lng:.6f})" for lat, lng in IFS_CELLS)
    op.execute(
        f"UPDATE weather_cells SET model = 'ecmwf_ifs' "
        f"WHERE (latitude, longitude) IN ({pairs})"
    )

    op.drop_constraint('uq_cell_coords', 'weather_cells', type_='unique')
    op.create_unique_constraint(
        'uq_cell_coords', 'weather_cells', ['model', 'latitude', 'longitude'])


def downgrade() -> None:
    # Reverting narrows the unique key back to (latitude, longitude). That is
    # only safe while no coordinate is shared between models; it currently is
    # not shared, but fail loudly rather than let MySQL drop the ambiguity.
    dupes = op.get_bind().execute(sa.text(
        "SELECT COUNT(*) FROM (SELECT latitude, longitude FROM weather_cells "
        "GROUP BY latitude, longitude HAVING COUNT(*) > 1) d"
    )).scalar()
    if dupes:
        raise RuntimeError(
            f"{dupes} coordinate(s) are held by more than one weather model; "
            "dropping weather_cells.model would make them indistinguishable. "
            "Delete the redundant model's cells first."
        )
    op.drop_constraint('uq_cell_coords', 'weather_cells', type_='unique')
    op.create_unique_constraint(
        'uq_cell_coords', 'weather_cells', ['latitude', 'longitude'])
    op.drop_column('weather_cells', 'model')
