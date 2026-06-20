#!/usr/bin/env python
"""Cross-model match between DeepSeek and Kimi datasets.

For papers analyzed by both models, match individual data rows on 5 fields
(POLYMER_PSMILES, DRUG_SMILES, WATER_PH, CONCENTRATION, CAPACITY) with
10% numeric tolerance and greedy assignment.

Flags matched rows in training_dataset_deepseek.csv (KIMI_MATCHED=True)
and outputs training_dataset_matched.csv (only matched rows).

Usage:  pixi run python scripts/match_model_datasets.py
"""

import csv
import sys
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
DEEPSEEK_FILE = REPO_DIR / "output" / "training_dataset_deepseek.csv"
KIMI_FILE = REPO_DIR / "output" / "training_dataset_kimi.csv"
OUTPUT_DIR = REPO_DIR / "output"
MATCHED_FILE = OUTPUT_DIR / "training_dataset_matched.csv"
TOLERANCE = 0.10


def _parse_float(val: str) -> float | None:
    val = val.strip()
    if not val or val.upper() == "NAN":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _within_tolerance(a: float | None, b: float | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    denom = max(abs(a), abs(b), 0.001)
    return abs(a - b) / denom <= TOLERANCE


def main():
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    for f in [DEEPSEEK_FILE, KIMI_FILE]:
        if not f.exists():
            logger.error(f"Input file not found: {f}")
            logger.error("Run resolve_smiles.py and build_training_dataset.py first")
            sys.exit(1)

    # Load datasets
    def load_csv(path):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    ds_rows = load_csv(DEEPSEEK_FILE)
    km_rows = load_csv(KIMI_FILE)
    logger.info(f"DeepSeek: {len(ds_rows)} rows")
    logger.info(f"Kimi:     {len(km_rows)} rows")

    # Group by paper
    ds_by_paper: dict[str, list[dict]] = {}
    km_by_paper: dict[str, list[dict]] = {}
    for r in ds_rows:
        ds_by_paper.setdefault(r.get("PAPER", ""), []).append(r)
    for r in km_rows:
        km_by_paper.setdefault(r.get("PAPER", ""), []).append(r)

    common_papers = sorted(set(ds_by_paper.keys()) & set(km_by_paper.keys()))
    logger.info(f"Papers in both: {len(common_papers)}")

    # Track which DeepSeek rows get matched
    matched_indices: set[int] = set()
    matched_rows: list[dict] = []

    for paper in common_papers:
        ds_paper_rows = ds_by_paper[paper]
        km_paper_rows = km_by_paper[paper]

        # Greedy matching within this paper
        used_ds: set[int] = set()
        used_km: set[int] = set()

        for i, ds_r in enumerate(ds_paper_rows):
            ds_poly = ds_r.get("POLYMER_PSMILES", "").lower()
            ds_drug = ds_r.get("DRUG_SMILES", "").lower()
            ds_ph = _parse_float(ds_r.get("WATER_PH", ""))
            ds_conc = _parse_float(ds_r.get("CONCENTRATION", ""))
            ds_cap = _parse_float(ds_r.get("CAPACITY", ""))

            for j, km_r in enumerate(km_paper_rows):
                if i in used_ds or j in used_km:
                    continue
                km_poly = km_r.get("POLYMER_PSMILES", "").lower()
                km_drug = km_r.get("DRUG_SMILES", "").lower()
                km_ph = _parse_float(km_r.get("WATER_PH", ""))
                km_conc = _parse_float(km_r.get("CONCENTRATION", ""))
                km_cap = _parse_float(km_r.get("CAPACITY", ""))

                if ds_poly != km_poly or ds_drug != km_drug:
                    continue
                if not _within_tolerance(ds_ph, km_ph):
                    continue
                if not _within_tolerance(ds_conc, km_conc):
                    continue
                if not _within_tolerance(ds_cap, km_cap):
                    continue

                used_ds.add(i)
                used_km.add(j)
                # Find index in original ds_rows list
                ds_idx = next(idx for idx, r in enumerate(ds_rows)
                              if r["POLYMER_PSMILES"] == ds_r["POLYMER_PSMILES"]
                              and r["DRUG_SMILES"] == ds_r["DRUG_SMILES"]
                              and r["WATER_PH"] == ds_r["WATER_PH"]
                              and r["CONCENTRATION"] == ds_r["CONCENTRATION"]
                              and r["CAPACITY"] == ds_r["CAPACITY"]
                              and r["PAPER"] == paper)
                matched_indices.add(ds_idx)
                matched_rows.append(dict(ds_r))
                break

    logger.info(f"Matched rows: {len(matched_rows)}")

    # Update training_dataset_deepseek.csv with KIMI_MATCHED flag
    for i, r in enumerate(ds_rows):
        if i in matched_indices:
            r["KIMI_MATCHED"] = "True"
        else:
            r["KIMI_MATCHED"] = "False"

    ds_cols = list(ds_rows[0].keys()) if ds_rows else []
    with open(DEEPSEEK_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ds_cols)
        writer.writeheader()
        writer.writerows(ds_rows)
    logger.info(f"Updated {DEEPSEEK_FILE} with KIMI_MATCHED flags")

    # Write matched dataset
    match_cols = list(matched_rows[0].keys()) if matched_rows else []
    with open(MATCHED_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=match_cols)
        writer.writeheader()
        writer.writerows(matched_rows)
    logger.info(f"Wrote {len(matched_rows)} matched rows to {MATCHED_FILE}")

    print()
    print(f"=== Cross-Model Match Results ===")
    print(f"Papers in common:       {len(common_papers)}")
    print(f"DeepSeek rows:          {len(ds_rows)}")
    print(f"Kimi rows:              {len(km_rows)}")
    print(f"Matched rows:           {len(matched_rows)}")
    matched_pct = len(matched_rows) / max(len(ds_rows) + len(km_rows) - len(matched_rows), 1) * 100
    print(f"Agreement rate:         {matched_pct:.0f}%")
    print(f"Matched file:           {MATCHED_FILE}")
    print()
    print("Notes:")
    print("  - training_dataset_deepseek.csv updated with KIMI_MATCHED column")
    print("  - training_dataset_matched.csv is the gold standard set")
    print("  - Use for LOOCV validation / quality floor")


if __name__ == "__main__":
    main()
