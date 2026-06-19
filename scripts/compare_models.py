#!/usr/bin/env python
"""Compare extraction results from two different model runs side by side.

Matches rows by all 5 fields (POLYMER, DRUG, pH, CONCENTRATION, CAPACITY)
with 10% tolerance for numeric fields.

Usage:
  pixi run python scripts/compare_models.py --new review_kimi-k2_6
  pixi run python scripts/compare_models.py --new review_kimi-k2_6 --csv
"""

import csv
import re
import sys
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
TOLERANCE = 0.10  # 10%


def _clean(val: str) -> str:
    val = val.strip()
    while val.startswith('"') and val.endswith('"') and len(val) >= 2:
        val = val[1:-1].strip()
    return val


def _parse_float(val: str) -> float | None:
    """Try to parse a value as float. Returns None if NaN or empty."""
    val = _clean(val)
    if not val or val.upper() == "NAN":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _within_tolerance(a: float | None, b: float | None) -> bool:
    """Check if two numeric values agree within 10% tolerance."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    denom = max(abs(a), abs(b), 0.001)
    return abs(a - b) / denom <= TOLERANCE


def parse_csv_rows(content: str) -> list[list[str]]:
    """Parse CSV rows from a model response file."""
    m = re.search(r"^# Response\s*\n(.+)$", content, re.DOTALL | re.MULTILINE)
    if not m:
        return []
    text = m.group(1).strip()
    if "NO USEFUL DATA" in text:
        return []
    rows = []
    for line in text.split("\n"):
        cells = [c.strip() for c in line.split(",")]
        if len(cells) < 3:
            continue
        first = cells[0].lower()
        if first in ("polymer_used", "polymer", "polymer name", "drug", "water_ph"):
            continue
        non_empty = sum(1 for c in cells[:6] if c and c.upper() != "NAN")
        if non_empty < 2:
            continue
        rows.append(cells[:6])
    return rows


def load_responses(responses_dir: Path) -> dict[str, list[list[str]]]:
    """Load all responses from a RESPONSES directory into {paper_name: rows}."""
    if not responses_dir.exists():
        logger.warning(f"Directory not found: {responses_dir}")
        return {}
    result: dict[str, list[list[str]]] = {}
    for paper_dir in sorted(responses_dir.iterdir()):
        if not paper_dir.is_dir():
            continue
        q_file = paper_dir / "q1.md"
        if not q_file.exists():
            continue
        content = q_file.read_text(encoding="utf-8")
        rows = parse_csv_rows(content)
        if rows:
            result[paper_dir.name] = rows
    return result


def _find_responses_dir(name: str) -> Path | None:
    candidates = [
        REPO_DIR / name,
        REPO_DIR / name / "RESPONSES",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            responses = c / "RESPONSES"
            if responses.exists():
                return responses
            return c
    return None


def count_matches(old_rows: list[list[str]], new_rows: list[list[str]]) -> int:
    """Count how many rows match between two sets, with greedy assignment."""
    used_old = set()
    used_new = set()
    matches = 0

    for i, o in enumerate(old_rows):
        o_poly = _clean(o[0]).lower()
        o_drug = _clean(o[1]).lower()
        o_ph = _parse_float(o[2]) if len(o) > 2 else None
        o_conc = _parse_float(o[3]) if len(o) > 3 else None
        o_cap = _parse_float(o[4]) if len(o) > 4 else None

        for j, n in enumerate(new_rows):
            if i in used_old or j in used_new:
                continue
            n_poly = _clean(n[0]).lower()
            n_drug = _clean(n[1]).lower()
            n_ph = _parse_float(n[2]) if len(n) > 2 else None
            n_conc = _parse_float(n[3]) if len(n) > 3 else None
            n_cap = _parse_float(n[4]) if len(n) > 4 else None

            if o_poly != n_poly or o_drug != n_drug:
                continue
            if not _within_tolerance(o_ph, n_ph):
                continue
            if not _within_tolerance(o_conc, n_conc):
                continue
            if not _within_tolerance(o_cap, n_cap):
                continue

            used_old.add(i)
            used_new.add(j)
            matches += 1
            break

    return matches


def compare_models(old_dir: str, new_dir: str, output_csv: bool = False):
    old_resp = _find_responses_dir(old_dir)
    new_resp = _find_responses_dir(new_dir)

    if old_resp is None or new_resp is None:
        logger.error(f"Could not find response directories")
        logger.error(f"  Tried old: {old_dir}")
        logger.error(f"  Tried new: {new_dir}")
        return

    old_data = load_responses(old_resp)
    new_data = load_responses(new_resp)

    common = sorted(set(old_data.keys()) & set(new_data.keys()))
    only_old = sorted(set(old_data.keys()) - set(new_data.keys()))
    only_new = sorted(set(new_data.keys()) - set(old_data.keys()))

    out_file = REPO_DIR / "model_comparison.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PAPER", "OLD_ROWS", "NEW_ROWS", "MATCH", "MISMATCH", "AGREEMENT"])

        total_old = 0
        total_new = 0
        total_match = 0
        for paper in common:
            old_rows = old_data[paper]
            new_rows = new_data[paper]
            matches = count_matches(old_rows, new_rows)
            total_old += len(old_rows)
            total_new += len(new_rows)
            total_match += matches
            mismatch = len(old_rows) + len(new_rows) - 2 * matches
            total = len(old_rows) + len(new_rows) - matches
            pct = f"{matches / max(total, 1) * 100:.0f}%"
            w.writerow([paper, len(old_rows), len(new_rows), matches, mismatch, pct])

        # Summary row
        grand_total = total_old + total_new - total_match
        grand_pct = f"{total_match / max(grand_total, 1) * 100:.0f}%"
        w.writerow(["TOTAL", total_old, total_new, total_match,
                     total_old + total_new - 2 * total_match, grand_pct])

    logger.info(f"Written to {out_file}")

    print(f"\n=== Model Comparison ===")
    print(f"Old ({old_resp.parent.name}): {len(old_data)} papers with data")
    print(f"New ({new_resp.parent.name}): {len(new_data)} papers with data")
    print(f"Common: {len(common)} papers")
    print(f"Only in old: {len(only_old)} papers")
    print(f"Only in new: {len(only_new)} papers")
    print()
    print(f"Total rows: OLD={total_old}  NEW={total_new}  MATCH={total_match}  ({grand_pct} agreement)")
    print(f"Comparison written to: {out_file}")


def test_usage():
    # Quick self-test
    assert _within_tolerance(100, 105) == True
    assert _within_tolerance(100, 120) == False
    assert _within_tolerance(None, None) == True
    assert _within_tolerance(100, None) == False
    assert _parse_float("10.5") == 10.5
    assert _parse_float("NaN") is None
    assert _parse_float("") is None
    # Test match counting
    old = [["PolyX", "Aspirin", "7.0", "10", "0.5", "doi"]]
    new_same = [["PolyX", "Aspirin", "7.0", "10", "0.5", "doi"]]
    new_diff = [["PolyX", "Aspirin", "7.0", "10", "0.6", "doi"]]
    assert count_matches(old, new_same) == 1
    assert count_matches(old, new_diff) == 0  # capacity diff > 10%
    print("All tests PASSED")


if __name__ == "__main__":
    old_dir = ""
    new_dir = ""
    to_csv = False
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--old" and i + 1 < len(args):
            old_dir = args[i + 1]
        elif a == "--new" and i + 1 < len(args):
            new_dir = args[i + 1]
        elif a == "--csv":
            to_csv = True
        elif a == "--test":
            test_usage()
            sys.exit(0)

    if not new_dir:
        print(__doc__)
        sys.exit(1)

    if not old_dir:
        old_dir = "opencode_go_deepseek_v4_flash_max_pdf2text_responses"

    compare_models(old_dir, new_dir, output_csv=to_csv)
