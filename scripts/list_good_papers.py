#!/usr/bin/env python
"""List papers ranked by data quality for manual review.

Shows a table of papers with the best data (HAS_POLYMER=yes, HAS_MOLECULE=yes)
sorted by data completeness. Use this to select which papers to re-analyze.

Usage:
  pixi run python scripts/list_good_papers.py                # terminal table (top 30)
  pixi run python scripts/list_good_papers.py --top 50       # top 50
  pixi run python scripts/list_good_papers.py --csv          # output CSV for reanalysis
  pixi run python scripts/list_good_papers.py --csv --all    # CSV with ALL good papers
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"
OUTPUT_CSV = REPO_DIR / "papers_for_review.csv"


def load_data() -> list[dict]:
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _clean(val: str) -> str:
    val = val.strip()
    while val.startswith('"') and val.endswith('"') and len(val) >= 2:
        val = val[1:-1].strip()
    return val


def score_row(row: dict) -> int:
    """Count how many of the 5 core fields have real values."""
    score = 0
    for col in ["POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION", "CAPACITY"]:
        v = _clean(row.get(col, ""))
        if v and v.upper() != "NAN":
            score += 1
    return score


def list_good_papers(top_n: int = 30, output_csv: bool = False, all_papers: bool = False):
    rows = load_data()

    # Group by paper name, only keep rows with HAS_POLYMER=yes + HAS_MOLECULE=yes
    papers: dict[str, dict] = {}
    for r in rows:
        if r.get("HAS_POLYMER") != "yes" or r.get("HAS_MOLECULE") != "yes":
            continue
        paper = _clean(r.get("PAPER", ""))
        if not paper:
            continue
        if paper not in papers:
            # Pick first analyzer found
            papers[paper] = {
                "paper": paper,
                "analyzer": _clean(r.get("ANALYZED_BY", "")),
                "rows": [],
            }
        papers[paper]["rows"].append(r)

    # Score each paper: count total rows with 4+ fields
    scored = []
    for paper, info in papers.items():
        good_rows = [r for r in info["rows"] if score_row(r) >= 4]
        total_rows = len(info["rows"])
        unique_polymers = set(_clean(r.get("POLYMER_USED", "")) for r in info["rows"])
        unique_drugs = set(_clean(r.get("DRUG", "")) for r in info["rows"])
        scored.append({
            "paper": paper,
            "analyzer": info["analyzer"],
            "good_rows": len(good_rows),
            "total_rows": total_rows,
            "polymers": len(unique_polymers),
            "drugs": len(unique_drugs),
        })

    scored.sort(key=lambda x: (-x["good_rows"], -x["total_rows"]))

    if not scored:
        logger.warning("No good papers found")
        return

    if output_csv:
        papers_to_process = scored if all_papers else scored[:top_n]
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["PAPER"])
            for p in papers_to_process:
                w.writerow([p["paper"]])
        logger.info(f"Wrote {len(papers_to_process)} papers to {OUTPUT_CSV}")
        return

    # Terminal table
    top = scored[:top_n]
    print(f"\n{'':>4} {'PAPER':<75} {'ROWS':>5} {'POLY':>5} {'DRUG':>5} {'MODEL'}")
    print("-" * 110)
    for i, p in enumerate(top, 1):
        name = p["paper"][:72] + "..." if len(p["paper"]) > 75 else p["paper"]
        model_short = "DS" if "deepseek" in p["analyzer"] else "GM" if "gemma" in p["analyzer"] else "?"
        print(f"{i:>4} {name:<75} {p['good_rows']:>5} {p['polymers']:>5} {p['drugs']:>5} {model_short}")
    print(f"\nTotal good papers: {len(scored)}")
    print(f"To export as CSV:  pixi run python scripts/list_good_papers.py --csv")
    print(f"To re-analyze:    bash scripts/reanalyze_papers.sh {OUTPUT_CSV}")
    print()


def test_usage():
    if not INPUT_FILE.exists():
        logger.warning(f"No input file at {INPUT_FILE}, skipping")
        return
    list_good_papers(top_n=5)


if __name__ == "__main__":
    top_n = 30
    to_csv = False
    all_papers = False

    args = sys.argv[1:]
    for a in args:
        if a.startswith("--top="):
            top_n = int(a.split("=")[1])
        elif a == "--csv":
            to_csv = True
        elif a == "--all":
            all_papers = True

    list_good_papers(top_n=top_n, output_csv=to_csv, all_papers=all_papers)
