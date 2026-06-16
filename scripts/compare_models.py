#!/usr/bin/env python
"""Compare extraction results from two different model runs side by side.

Usage:
  pixi run python scripts/compare_models.py --new gemma_review_mimo-v2_5
  pixi run python scripts/compare_models.py --old gemma4_26b-pdf2text-respones --new gemma_review_kimi-k2.7
  pixi run python scripts/compare_models.py --old opencode_go_deepseek_v4_flash_max_pdf2text_responses --new gemma_review_mimo-v2_5 --csv
"""

import csv
import re
import sys
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent


def _clean(val: str) -> str:
    val = val.strip()
    while val.startswith('"') and val.endswith('"') and len(val) >= 2:
        val = val[1:-1].strip()
    return val


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
    """Try to find a response directory by name or dir name."""
    candidates = [
        REPO_DIR / name,
        REPO_DIR / name / "RESPONSES",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            # If it's a model root dir (contains RESPONSES subdir)
            responses = c / "RESPONSES"
            if responses.exists():
                return responses
            return c
    return None


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

    # Find common papers
    common = sorted(set(old_data.keys()) & set(new_data.keys()))
    only_old = sorted(set(old_data.keys()) - set(new_data.keys()))
    only_new = sorted(set(new_data.keys()) - set(old_data.keys()))

    print(f"\n=== Model Comparison ===")
    print(f"Old ({old_resp.parent.name}): {len(old_data)} papers with data")
    print(f"New ({new_resp.parent.name}): {len(new_data)} papers with data")
    print(f"Common: {len(common)} papers")
    print(f"Only in old: {len(only_old)} papers")
    print(f"Only in new: {len(only_new)} papers")
    print()

    if output_csv:
        out_file = REPO_DIR / "model_comparison.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["PAPER", "OLD_ROWS", "NEW_ROWS", "MATCH", "DETAIL"])
            for paper in common:
                old_rows = old_data[paper]
                new_rows = new_data[paper]
                # Simple match: count exact (polymer, drug, cap) matches
                old_keys = {(r[0].lower(), r[1].lower(), _clean(r[4]) if len(r) > 4 else "") for r in old_rows}
                new_keys = {(r[0].lower(), r[1].lower(), _clean(r[4]) if len(r) > 4 else "") for r in new_rows}
                matches = old_keys & new_keys
                mismatch = len(old_keys | new_keys) - len(matches)
                w.writerow([paper, len(old_rows), len(new_rows), len(matches), f"{mismatch} mismatches"])
        logger.info(f"Written to {out_file}")
        return

    # Print comparison for common papers
    print(f"{'PAPER':<60} {'OLD':>5} {'NEW':>5} {'MATCH':>5} {'DIFF':>5}")
    print("-" * 85)
    total_old_rows = 0
    total_new_rows = 0
    total_matches = 0
    for paper in common:
        old_rows = old_data[paper]
        new_rows = new_data[paper]
        old_keys = {(r[0].lower(), r[1].lower(), _clean(r[4]) if len(r) > 4 else "") for r in old_rows}
        new_keys = {(r[0].lower(), r[1].lower(), _clean(r[4]) if len(r) > 4 else "") for r in new_rows}
        matches = old_keys & new_keys
        total_old_rows += len(old_rows)
        total_new_rows += len(new_rows)
        total_matches += len(matches)
        name = paper[:57] + "..." if len(paper) > 60 else paper
        print(f"{name:<60} {len(old_rows):>5} {len(new_rows):>5} {len(matches):>5} {len(old_keys ^ new_keys):>5}")

    print("-" * 85)
    print(f"{'TOTAL':<60} {total_old_rows:>5} {total_new_rows:>5} {total_matches:>5} {total_old_rows+total_new_rows-2*total_matches:>5}")
    print()
    if only_old:
        print(f"Only in old ({len(only_old)}): {', '.join(only_old[:5])}...")
    if only_new:
        print(f"Only in new ({len(only_new)}): {', '.join(only_new[:5])}...")


def test_usage():
    print("Run: pixi run python scripts/compare_models.py --new gemma_review_mimo-v2_5")


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

    if not new_dir:
        print(__doc__)
        sys.exit(1)

    if not old_dir:
        old_dir = "opencode_go_deepseek_v4_flash_max_pdf2text_responses"

    compare_models(old_dir, new_dir, output_csv=to_csv)
