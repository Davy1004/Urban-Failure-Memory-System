"""Parsing `data/raw/work_orders/` — 198 ward CSVs, three shapes, two schemas.

This is the only data source in the project independent of the complaint feed,
and it is the input to the allocation screen. Nothing here is loaded into
`complaints` or `interventions`; only the per-ward aggregate reaches the
database, in `ward_allocation`. That follows the precedent `ward_period_totals`
set: the table holds the aggregate of a source extract, and the extract itself
stays on disk.

Three parsing facts, each of which was a wrong number before it was a fixed one.

**Three file shapes, two schemas.** 20 files start with the header row; 163
open with a multi-line title cell and carry the same header on the second
record; 15 (wards 184-198) carry an entirely different legacy schema. Sniffing
for the header row rather than passing a fixed `skiprows` is what makes all 198
parse — the title cell contains newlines, so a line-based skip splits a record.

**Wards 184-198 have no End Date.** Their `brnumber` concatenates BR, CBR and
Rtgs numbers with dates. BR is the completion proxy: validated against the 183
files that carry both, BR sits at a median +22 days from End Date with 76.2%
within 90 days, while CBR is the bill-clearance date roughly two years later
(+621 days, 6.4% within 90). Using CBR would have been badly wrong (profile
§25.1). This recovers 125 drainage works and restores Bilekahalli, Begur,
Gottigere and Arakere to the panel.

**Drainage is keyword-classified, and that is a known weakness.** The patterns
live in `hazard_categories.yaml` beside the complaint categories, with the row
count each one matched. Many road works also mention drains, so a hand-curated
classifier would be better; the queue has that as a cosmetic item, because
profile §28 closed effectiveness for good and a better classifier now changes a
descriptive spend figure and nothing else.
"""
from __future__ import annotations

import logging
import pathlib
import re
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import yaml

from app.ingestion.bbmp_complaints import HAZARD_YAML

logger = logging.getLogger("ufms.derived.work_orders")

WORK_ORDER_DIR = pathlib.Path("data/raw/work_orders")
FILE_PATTERN = "ward_*.csv"
DATE_FORMAT = "%d-%b-%Y"

# "BR - 000110 / 30-Jun-2014CBR - 001796 / ..." — the BR date only, and only
# the first one, because the rest of the string is a different event.
BR_DATE = re.compile(r"BR\s*-\s*[^/]*/\s*(\d{2}-[A-Za-z]{3}-\d{4})")


@dataclass(frozen=True)
class WorkOrders:
    """Every parsed work order, with a drainage flag and a completion date."""
    rows: pd.DataFrame          # ward_no, description, completed_on, nett_cost, schema, is_drainage
    patterns: List[str]

    def drainage_in_window(self, start, end) -> pd.DataFrame:
        d = self.rows
        return d[d["is_drainage"]
                 & d["completed_on"].notna()
                 & (d["completed_on"] >= pd.Timestamp(start))
                 & (d["completed_on"] <= pd.Timestamp(end))]

    def spend_by_ward(self, start, end) -> pd.DataFrame:
        """Nett spend and work count per BBMP ward number, for the window."""
        w = self.drainage_in_window(start, end)
        return (w.groupby("ward_no")
                 .agg(drainage_works=("nett_cost", "size"),
                      drainage_spend=("nett_cost", "sum"))
                 .reset_index())


def drainage_patterns(path: pathlib.Path = HAZARD_YAML) -> List[str]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [p["pattern"] for p in doc["work_orders"]["drainage_patterns"]]


def _read_one(path: pathlib.Path) -> pd.DataFrame:
    """Read a ward file whatever shape it is in, header sniffed not assumed."""
    raw = pd.read_csv(path, dtype=str, low_memory=False, header=None)
    header_row = None
    for i in range(min(5, len(raw))):
        values = [str(v).strip() for v in raw.iloc[i].tolist()]
        if "Job Number" in values or "wo num" in values:
            header_row = i
            break
    if header_row is None:
        raise ValueError(
            f"{path.name}: no recognisable header in the first 5 rows. The file "
            f"is neither the main schema (has 'Job Number') nor the legacy one "
            f"(has 'wo num')."
        )
    df = raw.iloc[header_row + 1:].copy()
    df.columns = [str(v).strip() for v in raw.iloc[header_row].tolist()]
    return df.reset_index(drop=True)


def load_work_orders(raw_dir: pathlib.Path = WORK_ORDER_DIR,
                     patterns: Optional[List[str]] = None) -> WorkOrders:
    files = sorted(pathlib.Path(raw_dir).glob(FILE_PATTERN))
    if not files:
        raise FileNotFoundError(f"no {FILE_PATTERN} under {raw_dir}")
    pats = patterns if patterns is not None else drainage_patterns()
    rx = re.compile("|".join(re.escape(p) for p in pats), re.IGNORECASE)

    frames = []
    for path in files:
        ward_no = int(path.stem.split("_")[1])
        df = _read_one(path)
        if "Name of Work" in df.columns:
            completed = pd.to_datetime(df["End Date"], format=DATE_FORMAT,
                                       errors="coerce")
            frames.append(pd.DataFrame({
                "ward_no": ward_no,
                "description": df["Name of Work"].fillna(""),
                "completed_on": completed,
                "nett_cost": pd.to_numeric(df["Nett"], errors="coerce"),
                "schema": "main",
            }))
        else:
            br = df["brnumber"].fillna("").str.extract(BR_DATE)[0]
            frames.append(pd.DataFrame({
                "ward_no": ward_no,
                "description": df["wodetails"].fillna(""),
                "completed_on": pd.to_datetime(br, format=DATE_FORMAT,
                                               errors="coerce"),
                "nett_cost": pd.to_numeric(df["nett"], errors="coerce"),
                "schema": "legacy",
            }))

    rows = pd.concat(frames, ignore_index=True)
    rows["is_drainage"] = rows["description"].str.contains(rx)
    logger.info("work orders: %d rows over %d wards (%d legacy), %d drainage",
                len(rows), rows["ward_no"].nunique(),
                int((rows["schema"] == "legacy").sum()),
                int(rows["is_drainage"].sum()))
    return WorkOrders(rows=rows, patterns=pats)
