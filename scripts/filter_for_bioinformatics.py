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


def _clean_val(val: str) -> str:
    """Clean a value: strip whitespace and remove extra quotes."""
    val = val.strip()
    while val.startswith('"') and val.endswith('"') and len(val) >= 2:
        val = val[1:-1].strip()
    return val


def try_lookup(name: str, lookup_dict: dict) -> str:
    """Try to find a name in the lookup dictionary."""
    clean = _clean_val(name)
    if clean in lookup_dict:
        return lookup_dict[clean]
    for k, v in lookup_dict.items():
        if k.lower() == clean.lower():
            return v
    return ""


def filter_and_deduplicate() -> Path:
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Step 1: Keep rows with a known polymer + known molecule
    filtered = [r for r in rows if r.get("HAS_POLYMER") == "yes" and r.get("HAS_MOLECULE") == "yes"]
    logger.info(f"Rows with polymer + molecule: {len(filtered)} / {len(rows)}")

    # Step 2: Sort: deepseek first (preferred), then gemma text, then gemma image
    def analyzer_rank(r):
        a = r.get("ANALYZED_BY", "")
        if "deepseek" in a:
            return 0
        if "pdf2text" in a:
            return 1
        return 2

    filtered.sort(key=analyzer_rank)

    # Step 3: Deduplicate by (polymer, drug, pH, concentration)
    seen: set[str] = set()
    deduped = []
    for r in filtered:
        polymer = _clean_val(r.get("POLYMER_USED", "")).lower()
        drug = _clean_val(r.get("DRUG", "")).lower()
        ph = r.get("WATER_PH", "").strip().lower()
        conc = r.get("CONCENTRATION", "").strip().lower()
        key = f"{polymer}|{drug}|{ph}|{conc}"
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    logger.info(f"After dedup: {len(deduped)} rows (from {len(filtered)})")

    # Step 4: Write final CSV (clean values, PDCC-compatible columns only)
    base_cols = ["POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE"]
    extra_cols = ["POLYMER_PSMILES", "DRUG_SMILES"]
    out_cols = base_cols + extra_cols

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
        writer.writeheader()
        for r in deduped:
            row = {col: _clean_val(r.get(col, "")) for col in base_cols}
            row["POLYMER_PSMILES"] = try_lookup(r.get("POLYMER_USED", ""), PSMILES_DICT)
            row["DRUG_SMILES"] = try_lookup(r.get("DRUG", ""), SMILES_DICT)
            writer.writerow(row)

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
