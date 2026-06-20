#!/usr/bin/env python
"""Build ML-ready training datasets from classified data + SMILES/PSMILES mappings.

Inputs:
  classified_adsorption_data.csv   — all classified rows
  output/drug_smiles.json          — {drug_name: smiles}
  output/polymer_psmiles.json      — {polymer_name: psmiles}

Outputs:
  output/training_dataset_deepseek.csv  — DeepSeek-only rows with PSMILES+SMILES
  output/training_dataset_kimi.csv      — Kimi-only rows (for matching)
  output/training_dataset.csv           — all valid rows combined
"""

import csv
import json
import sys
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"
DRUG_SMILES_FILE = REPO_DIR / "output" / "drug_smiles.json"
POLYMER_PSMILES_FILE = REPO_DIR / "output" / "polymer_psmiles.json"
OUTPUT_DIR = REPO_DIR / "output"


def _clean(val):
    val = val.strip()
    while val.startswith('"') and val.endswith('"') and len(val) >= 2:
        val = val[1:-1].strip()
    return val


def main():
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load SMILES mappings
    with open(DRUG_SMILES_FILE, encoding="utf-8") as f:
        drug_smiles = json.load(f)
    with open(POLYMER_PSMILES_FILE, encoding="utf-8") as f:
        polymer_psmiles = json.load(f)
    logger.info(f"Loaded {len(drug_smiles)} drug SMILES and {len(polymer_psmiles)} polymer PSMILES")

    # Load classified data
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    logger.info(f"Loaded {len(all_rows)} rows from {INPUT_FILE}")

    # Filter to valid rows
    valid = [
        r for r in all_rows
        if r.get("HAS_POLYMER") == "yes"
        and r.get("HAS_MOLECULE") == "yes"
        and r.get("HAS_WATER_PH") == "yes"
        and r.get("HAS_CONCENTRATION") == "yes"
        and r.get("HAS_CAPACITY") == "yes"
    ]
    logger.info(f"Valid rows (all5): {len(valid)}")

    # Apply SMILES/PSMILES mappings
    out_cols = ["POLYMER_USED", "DRUG", "POLYMER_PSMILES", "DRUG_SMILES",
                "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE",
                "ANALYZED_BY", "PAPER"]

    def build_row(r):
        poly = _clean(r.get("POLYMER_USED", ""))
        drug = _clean(r.get("DRUG", ""))
        return {
            "POLYMER_USED": poly,
            "DRUG": drug,
            "POLYMER_PSMILES": polymer_psmiles.get(poly, ""),
            "DRUG_SMILES": drug_smiles.get(drug, ""),
            "WATER_PH": _clean(r.get("WATER_PH", "")),
            "CONCENTRATION": _clean(r.get("CONCENTRATION", "")),
            "CAPACITY": _clean(r.get("CAPACITY", "")),
            "SOURCE": _clean(r.get("SOURCE", "")),
            "ANALYZED_BY": _clean(r.get("ANALYZED_BY", "")),
            "PAPER": _clean(r.get("PAPER", "")),
        }

    all_rows_out = [build_row(r) for r in valid]

    # Drop rows where PSMILES or SMILES are empty / invalid
    filtered = []
    for r in all_rows_out:
        psmiles = r["POLYMER_PSMILES"]
        if not psmiles or psmiles in ("NOT_A_VALID_POLYMER", "UNABLE_TO_RESOLVE"):
            continue
        if not r["DRUG_SMILES"]:
            continue
        filtered.append(r)
    logger.info(f"After removing unresolved SMILES: {len(filtered)} rows")

    # Deduplicate within each model (same (polymer, drug, pH, conc, cap))
    def dedup_key(r):
        return f"{r['POLYMER_PSMILES']}|{r['DRUG_SMILES']}|{r['WATER_PH']}|{r['CONCENTRATION']}|{r['CAPACITY']}"

    seen_ds = set()
    seen_km = set()
    seen_all = set()
    deepseek_rows = []
    kimi_rows = []
    combined_rows = []

    for r in filtered:
        key = dedup_key(r)
        model = r["ANALYZED_BY"].lower()
        if key not in seen_all:
            seen_all.add(key)
            combined_rows.append(r)
        if "deepseek" in model:
            if key not in seen_ds:
                seen_ds.add(key)
                deepseek_rows.append(r)
        elif "kimi" in model:
            if key not in seen_km:
                seen_km.add(key)
                kimi_rows.append(r)

    logger.info(f"DeepSeek deduplicated: {len(deepseek_rows)}")
    logger.info(f"Kimi deduplicated: {len(kimi_rows)}")
    logger.info(f"Combined deduplicated: {len(combined_rows)}")

    # Add KIMI_MATCHED flag (initially all False) for deepseek
    deepseek_with_flag = []
    for r in deepseek_rows:
        r["KIMI_MATCHED"] = "False"
        deepseek_with_flag.append(r)

    ds_cols = out_cols + ["KIMI_MATCHED"]

    # Write output files
    def write_csv(filename, rows, cols):
        path = OUTPUT_DIR / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Wrote {len(rows)} rows to {path}")
        return path

    write_csv("training_dataset_deepseek.csv", deepseek_with_flag, ds_cols)
    write_csv("training_dataset_kimi.csv", kimi_rows, out_cols)
    write_csv("training_dataset.csv", combined_rows, out_cols)

    print()
    print(f"=== Summary ===")
    print(f"training_dataset_deepseek.csv: {len(deepseek_with_flag)} rows (with KIMI_MATCHED flag)")
    print(f"training_dataset_kimi.csv:     {len(kimi_rows)} rows")
    print(f"training_dataset.csv:          {len(combined_rows)} rows (all models)")


if __name__ == "__main__":
    main()
