#!/usr/bin/env python
"""Filter classified data to high-priority rows and prepare for lele-bioinformatics.

Input: classified_adsorption_data.csv
Output: ready_for_bioinformatics.csv

Steps:
  1. Keep only PRIORITY=high rows (real polymer + real molecule + good data)
  2. Deduplicate (same (polymer, drug, pH, conc)) — prefer deepseek over gemma
  3. Attempt PSMILES/SMILES lookup using lele-bioinformatics dictionaries if available
"""

import csv
import sys
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).parent.parent
INPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"
OUTPUT_FILE = REPO_DIR / "ready_for_bioinformatics.csv"

# Optional: try to load PSMILES/SMILES dicts from sibling project
LELE_BIO_DIR = REPO_DIR.parent / "lele-py-bioinformatics"

PSMILES_DICT: dict[str, str] = {}
SMILES_DICT: dict[str, str] = {}

try:
    if LELE_BIO_DIR.exists():
        sys.path.insert(0, str(LELE_BIO_DIR))
        from bio.__global__ import PSMILES_DICT as _PD, SMILES_DICT as _SD
        PSMILES_DICT = dict(_PD)
        SMILES_DICT = dict(_SD)
        logger.info(f"Loaded {len(PSMILES_DICT)} PSMILES and {len(SMILES_DICT)} SMILES from lele-bioinformatics")
    else:
        logger.warning(f"lele-bioinformatics not found at {LELE_BIO_DIR}, skipping SMILES lookup")
except Exception as e:
    logger.warning(f"Could not load SMILES from lele-bioinformatics: {e}")


def try_lookup(name: str, lookup_dict: dict) -> str:
    """Try to find a name in the lookup dictionary."""
    clean = name.strip().strip('"').strip("'")
    if clean in lookup_dict:
        return lookup_dict[clean]
    # Try case-insensitive
    for k, v in lookup_dict.items():
        if k.lower() == clean.lower():
            return v
    return ""


def filter_and_deduplicate() -> Path:
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Step 1: Keep only high priority
    high = [r for r in rows if r.get("PRIORITY", "") == "high"]
    logger.info(f"High priority rows: {len(high)} / {len(rows)}")

    # Step 2: Sort: deepseek first (preferred), then gemma text, then gemma image
    def analyzer_rank(r):
        a = r.get("ANALYZED_BY", "")
        if "deepseek" in a:
            return 0
        if "pdf2text" in a:
            return 1
        return 2

    high.sort(key=analyzer_rank)

    # Step 3: Deduplicate by (polymer, drug, pH, concentration)
    seen: set[str] = set()
    deduped = []
    for r in high:
        polymer = r.get("POLYMER_USED", "").strip().lower()
        drug = r.get("DRUG", "").strip().lower()
        ph = r.get("WATER_PH", "").strip().lower()
        conc = r.get("CONCENTRATION", "").strip().lower()
        key = f"{polymer}|{drug}|{ph}|{conc}"
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    logger.info(f"After dedup: {len(deduped)} rows (from {len(high)})")

    # Step 4: Attempt SMILES lookup
    fieldnames = reader.fieldnames or list(rows[0].keys())
    has_smiles = bool(PSMILES_DICT) or bool(SMILES_DICT)
    if has_smiles:
        fieldnames = fieldnames + ["POLYMER_PSMILES", "DRUG_SMILES"]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in deduped:
            if has_smiles:
                r["POLYMER_PSMILES"] = try_lookup(r.get("POLYMER_USED", ""), PSMILES_DICT)
                r["DRUG_SMILES"] = try_lookup(r.get("DRUG", ""), SMILES_DICT)
            writer.writerow(r)

    logger.info(f"Output: {OUTPUT_FILE} ({len(deduped)} rows)")
    return OUTPUT_FILE


def test_usage():
    if not INPUT_FILE.exists():
        logger.warning(f"No input file at {INPUT_FILE}, skipping")
        return
    out = filter_and_deduplicate()
    rows = sum(1 for _ in open(out, encoding="utf-8")) - 1
    logger.info(f"Filtered to {rows} rows")


if __name__ == "__main__":
    filter_and_deduplicate()
