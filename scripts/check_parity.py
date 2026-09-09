"""Prove a deployed instance serves the same numbers as local - or fail loudly.

    # one instance: are the frozen numbers right?
    python scripts/check_parity.py --base http://127.0.0.1:8000

    # two instances: do they agree, field by field?
    python scripts/check_parity.py \
        --base http://127.0.0.1:8000 \
        --other https://ufms-api.onrender.com --other-password 'the-generated-one'

Why
---
A deployment that returns 200 on every endpoint can still be wrong: pointed at
an empty database, at a database whose `derive` step never ran, or at one whose
restore silently dropped rows. All three render as a dashboard that looks
plausible and is not the system. The only check that catches them is comparing
the numbers.

So this does two things, and the first works with one URL:

**Invariants.** The frozen figures, asserted against whatever instance is named.
These are not thresholds to tune - they are the published results, and if an
instance disagrees with any of them it must not be shown to anyone.

**Diff.** Every field of all five endpoint payloads, compared between two
instances, to a relative tolerance of 1e-9. Nothing here is genuinely volatile:
`computed_at` and `snapshot_id` are stored columns carried by the dump, not
per-request values, so an honest deployment matches exactly and any difference
at all is a finding.

Exit status is 0 only if everything passed, so this can gate a demo.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from typing import Any

# The endpoints the dashboard reads, in the order the demo visits them.
ENDPOINTS: tuple[str, ...] = (
    "/api/v1/watchlist",
    "/api/v1/index",
    "/api/v1/index/Jakkur",
    "/api/v1/emerging",
    "/api/v1/allocation",
)

TOLERANCE = 1e-9

# The published results. Sources, in order: docs/01-evaluation-rules.md's IFS
# triple; profile section 25.1 and docs/figures/README.md for the emerging
# evidence; the allocation finding as stated in CLAUDE.md.
#
# Each entry is (endpoint, dotted path, expected, absolute tolerance). The
# tolerances are the precision the number is quoted to, not a fudge factor.
INVARIANTS: tuple[tuple[str, str, Any, float], ...] = (
    # Triage: the three figures that must always travel together.
    ("/api/v1/watchlist", "context.precision_at_k", 0.14080882, 5e-9),
    ("/api/v1/watchlist", "context.oracle_at_k", 0.37720588, 5e-9),
    ("/api/v1/watchlist", "context.random_at_k", 0.04786839, 5e-9),
    ("/api/v1/watchlist", "context.test_rain_days", 136, 0),
    ("/api/v1/watchlist", "context.test_events", 1289, 0),
    ("/api/v1/watchlist", "context.weather_model", "ecmwf_ifs", 0),
    ("/api/v1/watchlist", "k", 20, 0),
    # Allocation: spend tracks area, not need. Both halves, because the
    # contrast between them is the entire finding.
    ("/api/v1/allocation", "finding.spend_vs_area.rho", 0.4740946, 5e-8),
    ("/api/v1/allocation", "finding.spend_vs_pre_index.rho", 0.0824532, 5e-8),
    ("/api/v1/allocation", "finding.spend_vs_pre_index.p", 0.3918004, 5e-8),
    ("/api/v1/allocation", "finding.spend_vs_events_controlling_area.rho", -0.0500933, 5e-8),
    ("/api/v1/allocation", "finding.n_wards", 110, 0),
    ("/api/v1/allocation", "finding.n_treated", 103, 0),
    # Emerging: chronically above norm, and no ground truth.
    ("/api/v1/emerging", "eligible_wards", 103, 0),
    ("/api/v1/emerging", "flagged", 10, 0),
    ("/api/v1/emerging", "ground_truth_available", False, 0),
    ("/api/v1/emerging", "evidence.flagged_above_norm", 10, 0),
    ("/api/v1/emerging", "evidence.p_vs_other_wards", 0.00014412896, 5e-11),
    ("/api/v1/emerging", "evidence.p_vs_own_first_half", 0.11621094, 5e-9),
    # The case study series.
    ("/api/v1/index/Jakkur", "ward", "Jakkur", 0),
    ("/api/v1/index/Jakkur", "quarters", 20, 0),
    ("/api/v1/index/Jakkur", "mean_rel_index", 1.0947569, 5e-8),
    # The choropleth needs all 198 wards in one response; a short list renders
    # as unshaded wards, which read as "nothing happened here".
    ("/api/v1/index", "wards.__len__", 198, 0),
)

# The frozen top-20, in rank order. Reordered or substituted entries mean the
# watchlist is not the one the paper reports.
FROZEN_TOP20: tuple[str, ...] = (
    "Bellandur", "Horamavu", "Thanisandra", "Begur", "Ramamurthy Nagar",
)


class Client:
    def __init__(self, base: str, email: str, password: str) -> None:
        self.base = base.rstrip("/")
        self.email = email
        self.password = password
        self.token: str | None = None

    def _call(self, path: str, body: dict | None = None) -> Any:
        req = urllib.request.Request(self.base + path)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            req.add_header("Content-Type", "application/json")
            req.method = "POST"
        try:
            # A cold free-tier instance can take a minute to wake, and that is
            # a slow instance rather than a broken one.
            with urllib.request.urlopen(req, data=data, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:400]
            raise SystemExit(f"{self.base}{path} -> HTTP {e.code}\n  {detail}")
        except urllib.error.URLError as e:
            raise SystemExit(f"{self.base}{path} -> unreachable: {e.reason}")

    def login(self) -> None:
        res = self._call(
            "/api/v1/auth/login", {"email": self.email, "password": self.password}
        )
        self.token = res["access_token"]

    def get(self, path: str) -> Any:
        return self._call(path)


def dig(obj: Any, path: str) -> Any:
    """Walk a dotted path. `__len__` on a list gives its length."""
    cur = obj
    for part in path.split("."):
        if part == "__len__":
            return len(cur)
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def close(a: Any, b: Any, tol: float) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if tol == 0:
            return a == b
        return math.isclose(a, b, rel_tol=0.0, abs_tol=tol)
    return a == b


def diff(a: Any, b: Any, path: str = "") -> list[str]:
    """Every place two payloads disagree, as dotted paths."""
    out: list[str] = []
    if type(a) is not type(b) and not (
        isinstance(a, (int, float)) and isinstance(b, (int, float))
    ):
        return [f"{path or '<root>'}: type {type(a).__name__} vs {type(b).__name__}"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: missing on the first instance")
            elif k not in b:
                out.append(f"{path}.{k}: missing on the second instance")
            else:
                out += diff(a[k], b[k], f"{path}.{k}" if path else k)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: {len(a)} items vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        if not math.isclose(a, b, rel_tol=TOLERANCE, abs_tol=1e-15):
            out.append(f"{path}: {a!r} vs {b!r}")
    elif a != b:
        out.append(f"{path}: {a!r} vs {b!r}")
    return out


def check_invariants(label: str, payloads: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for endpoint, path, expected, tol in INVARIANTS:
        try:
            actual = dig(payloads[endpoint], path)
        except (KeyError, IndexError, TypeError) as e:
            failures.append(f"{endpoint} {path}: not present ({e})")
            continue
        if not close(actual, expected, tol):
            failures.append(f"{endpoint} {path}: expected {expected!r}, got {actual!r}")

    items = payloads["/api/v1/watchlist"]["items"]
    ranks = [i["rank_position"] for i in items]
    if ranks != list(range(1, len(items) + 1)):
        failures.append(f"watchlist rank_position is not 1..n: {ranks}")
    top = [i["ward"] for i in items[: len(FROZEN_TOP20)]]
    if tuple(top) != FROZEN_TOP20:
        failures.append(
            f"watchlist head is not the frozen order:\n"
            f"    expected {list(FROZEN_TOP20)}\n"
            f"    got      {top}"
        )

    # The retraction and the caveats are required response fields precisely so a
    # redesign cannot drop them. Check the deployed instance still carries them.
    if not payloads["/api/v1/allocation"].get("retraction"):
        failures.append("allocation.retraction is empty - the retraction must ship")
    if not payloads["/api/v1/emerging"].get("caveats"):
        failures.append("emerging.caveats is empty - the caveats must ship")

    print(f"  {label}: {len(INVARIANTS) + 4 - len(failures)}/{len(INVARIANTS) + 4} checks passed")
    return failures


def collect(c: Client) -> dict[str, Any]:
    c.login()
    return {e: c.get(e) for e in ENDPOINTS}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--email", default="demo.officer@ufms-demo.org")
    ap.add_argument("--password", default="ufms-demo-2026")
    ap.add_argument("--other", help="a second instance to diff against --base")
    ap.add_argument("--other-email", help="defaults to --email")
    ap.add_argument("--other-password", help="defaults to --password")
    args = ap.parse_args()

    print(f"Frozen invariants, {len(INVARIANTS) + 4} of them")
    base_payloads = collect(Client(args.base, args.email, args.password))
    failures = check_invariants(args.base, base_payloads)

    if args.other:
        other_payloads = collect(
            Client(
                args.other,
                args.other_email or args.email,
                args.other_password or args.password,
            )
        )
        failures += [f"{args.other}: {f}" for f in check_invariants(args.other, other_payloads)]

        print(f"\nField-by-field diff, relative tolerance {TOLERANCE:g}")
        total = 0
        for e in ENDPOINTS:
            d = diff(base_payloads[e], other_payloads[e])
            total += len(d)
            print(f"  {e:<28} {'identical' if not d else str(len(d)) + ' differences'}")
            for line in d[:15]:
                print(f"      {line}")
            if len(d) > 15:
                print(f"      ... and {len(d) - 15} more")
        if total:
            failures.append(
                f"{total} field differences between the two instances - the deployed "
                "instance is not serving the same numbers, so it is broken, not deployed"
            )

    print()
    if failures:
        print(f"FAILED - {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASSED" + (" - both instances agree, and on the published numbers" if args.other else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
