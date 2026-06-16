#!/usr/bin/env python
"""Select papers for re-analysis with another AI model.

Reads classified_adsorption_data.csv, applies selectors, writes papers_for_review.csv.

Usage:
  pixi run python scripts/select_for_review.py --dense 5 --diverse 3 --overlap --complete 5
  pixi run python scripts/select_for_review.py --dense all       # all good papers
  pixi run python scripts/select_for_review.py --complete 10 --diverse 3
  pixi run python scripts/select_for_review.py --dense all --complete all
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"
OUTPUT_FILE = REPO_DIR / "papers_for_review.csv"


def _clean(val: str) -> str:
    val = val.strip()
    while val.startswith('"') and val.endswith('"') and len(val) >= 2:
        val = val[1:-1].strip()
    return val


def _classify_polymer(polymer: str) -> str:
    p = _clean(polymer).lower()
    if re.search(r"composite|hybrid|nanocomposite", p):
        return "composite"
    if re.search(r"hydrogel|cryogel|aerogel", p):
        return "hydrogel_cryogel"
    if re.search(r"modified|grafted|functionalized|cross.?link", p):
        return "functionalized"
    if re.search(r"poly|mer\b|acrylamid|vinyl|styrene|urethane|imide", p):
        return "synthetic_polymer"
    if re.search(r"chitosan|cellulose|alginate|starch|gelatin|dextran|agarose|carrageenan|pectin", p):
        return "biopolymer"
    return "other"


def load_data() -> list[dict]:
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _parse_n(val: str) -> int | None:
    """Parse a value: int for numbers, None for 'all'."""
    if val.lower() == "all":
        return None
    return int(val)


def selector_dense(rows: list[dict], n: int | None) -> list[str]:
    """Top N papers by most data rows (HAS_POLYMER=yes + HAS_MOLECULE=yes)."""
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r.get("HAS_POLYMER") == "yes" and r.get("HAS_MOLECULE") == "yes":
            paper = _clean(r.get("PAPER", ""))
            if paper:
                counts[paper] += 1
    sorted_papers = [p for p, _ in sorted(counts.items(), key=lambda x: -x[1])]
    selected = sorted_papers if n is None else sorted_papers[:n]
    logger.info(f"--dense {n or 'all'}: {len(selected)} papers")
    return selected


def selector_diverse(rows: list[dict], n: int | None) -> list[str]:
    """N papers spanning different polymer categories."""
    papers_by_category: dict[str, list[tuple[str, int]]] = defaultdict(list)
    paper_rows: dict[str, int] = defaultdict(int)
    paper_polymer: dict[str, str] = {}

    for r in rows:
        if r.get("HAS_POLYMER") != "yes" or r.get("HAS_MOLECULE") != "yes":
            continue
        paper = _clean(r.get("PAPER", ""))
        polymer = _clean(r.get("POLYMER_USED", ""))
        if not paper or not polymer:
            continue
        paper_rows[paper] += 1
        paper_polymer[paper] = polymer

    for paper, polymer in paper_polymer.items():
        cat = _classify_polymer(polymer)
        papers_by_category[cat].append((paper, paper_rows[paper]))

    # Pick best paper from each category, round-robin up to N (or all)
    selected = []
    ordered_cats = ["synthetic_polymer", "biopolymer", "hydrogel_cryogel", "composite", "functionalized", "other"]
    while n is None or len(selected) < n:
        picked_any = False
        for cat in ordered_cats:
            if cat not in papers_by_category:
                continue
            cat_papers = papers_by_category[cat]
            best = max(cat_papers, key=lambda x: x[1])
            if best[0] not in selected:
                selected.append(best[0])
                cat_papers.remove(best)
                if not cat_papers:
                    del papers_by_category[cat]
                picked_any = True
                if n is not None and len(selected) >= n:
                    break
        if not picked_any:
            break

    logger.info(f"--diverse {n or 'all'}: {len(selected)} papers")
    return selected


def selector_overlap(rows: list[dict]) -> list[str]:
    """Papers analyzed by 2+ models where BOTH returned data."""
    paper_analyzers: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r.get("HAS_POLYMER") == "yes" and r.get("HAS_MOLECULE") == "yes":
            paper = _clean(r.get("PAPER", ""))
            analyzer = _clean(r.get("ANALYZED_BY", ""))
            if paper and analyzer:
                paper_analyzers[paper].add(analyzer)

    selected = [p for p, aa in paper_analyzers.items() if len(aa) >= 2]
    logger.info(f"--overlap: {len(selected)} papers with 2+ models")
    return selected


def selector_complete(rows: list[dict], n: int | None) -> list[str]:
    """Top N papers where all 5 core fields have values."""
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if (r.get("HAS_POLYMER") == "yes" and r.get("HAS_MOLECULE") == "yes"
                and r.get("HAS_WATER_PH") == "yes" and r.get("HAS_CONCENTRATION") == "yes"
                and r.get("HAS_CAPACITY") == "yes"):
            paper = _clean(r.get("PAPER", ""))
            if paper:
                counts[paper] += 1
    sorted_papers = [p for p, _ in sorted(counts.items(), key=lambda x: -x[1])]
    selected = sorted_papers if n is None else sorted_papers[:n]
    logger.info(f"--complete {n or 'all'}: {len(selected)} papers")
    return selected


def main():
    dense_n = -1
    diverse_n = -1
    do_overlap = False
    complete_n = -1

    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--dense" and i + 1 < len(args):
            dense_n = _parse_n(args[i + 1])
        elif a == "--diverse" and i + 1 < len(args):
            diverse_n = _parse_n(args[i + 1])
        elif a == "--overlap":
            do_overlap = True
        elif a == "--complete" and i + 1 < len(args):
            complete_n = _parse_n(args[i + 1])

    if dense_n == -1 and diverse_n == -1 and not do_overlap and complete_n == -1:
        print(__doc__)
        return

    rows = load_data()
    selected: list[str] = []
    seen: set[str] = set()

    def add(papers: list[str]):
        for p in papers:
            if p not in seen:
                seen.add(p)
                selected.append(p)

    if dense_n != -1:
        add(selector_dense(rows, dense_n))
    if diverse_n != -1:
        add(selector_diverse(rows, diverse_n))
    if do_overlap:
        add(selector_overlap(rows))
    if complete_n != -1:
        add(selector_complete(rows, complete_n))

    # Write output
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PAPER"])
        for paper in selected:
            w.writerow([paper])

    logger.info(f"Total: {len(selected)} papers written to {OUTPUT_FILE}")
    for i, p in enumerate(selected, 1):
        rows_count = sum(1 for r in rows if _clean(r.get("PAPER", "")) == p)
        polymer = next((_clean(r.get("POLYMER_USED", "")) for r in rows if _clean(r.get("PAPER", "")) == p), "?")
        logger.info(f"  {i:>3}. {p[:60]:<62} ({rows_count} rows, {polymer})")


def test_usage():
    if not INPUT_FILE.exists():
        logger.warning(f"No input at {INPUT_FILE}")
        return
    main()


if __name__ == "__main__":
    main()
