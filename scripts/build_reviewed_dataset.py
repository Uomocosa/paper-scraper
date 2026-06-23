import json
from pathlib import Path

import pandas as pd
from loguru import logger

REVIEW_DIR = Path(__file__).resolve().parent.parent / "claude_opus_4_8_review"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def load_drug_smiles(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)
    result = {}
    for name, entry in data.items():
        smiles = entry.get("smiles")
        if smiles:
            result[name.lower()] = smiles
    logger.info(f"Loaded {len(result)} drug SMILES (skipped {sum(1 for e in data.values() if not e.get('smiles'))} nulls)")
    return result


def load_polymer_psmiles(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)
    result = {}
    skipped_composite = 0
    skipped_null = 0
    for name, entry in data.items():
        psmiles = entry.get("p_smiles")
        if psmiles is None:
            if entry.get("components"):
                skipped_composite += 1
            else:
                skipped_null += 1
            continue
        result[name.lower()] = psmiles
    logger.info(f"Loaded {len(result)} polymer PSMILES (skipped {skipped_composite} composites, {skipped_null} nulls)")
    return result


def main():
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    drug_smiles = load_drug_smiles(REVIEW_DIR / "drugs_smiles.json")
    polymer_psmiles = load_polymer_psmiles(REVIEW_DIR / "polymers_psmiles.json")

    df_main = pd.read_csv(REVIEW_DIR / "adsorption_data.csv")
    df_rsm = pd.read_csv(REVIEW_DIR / "adsorption_data_rsm_supplementary.csv")
    df_rsm = df_rsm.drop(columns=["CONTACT_TIME_MIN"], errors="ignore")

    common_cols = [c for c in df_main.columns if c in df_rsm.columns]
    df = pd.concat([df_main[common_cols], df_rsm[common_cols]], ignore_index=True)
    logger.info(f"Merged: {len(df_main)} main + {len(df_rsm)} RSM = {len(df)} total")

    before = len(df)
    df = df.dropna(subset=["CONCENTRATION"])
    logger.info(f"Dropped {before - len(df)} rows with NaN CONCENTRATION ({len(df)} remaining)")

    # Map DRUG → DRUG_SMILES (case-insensitive)
    drug_lower = df["DRUG"].astype(str).str.lower().str.strip()
    df["DRUG_SMILES"] = drug_lower.map(drug_smiles)
    missing_drugs = set(drug_lower[df["DRUG_SMILES"].isna()].unique())
    if missing_drugs:
        logger.warning(f"Drugs missing from drug_smiles.json: {missing_drugs}")

    # Map POLYMER_USED → POLYMER_PSMILES (case-insensitive)
    poly_lower = df["POLYMER_USED"].astype(str).str.lower().str.strip()
    df["POLYMER_PSMILES"] = poly_lower.map(polymer_psmiles)
    missing_polymers = set(poly_lower[df["POLYMER_PSMILES"].isna()].unique())
    if missing_polymers:
        logger.warning(f"Polymers missing from polymers_psmiles.json: {missing_polymers}")

    before = len(df)
    df = df.dropna(subset=["DRUG_SMILES", "POLYMER_PSMILES"])
    logger.info(f"Dropped {before - len(df)} rows with unresolved SMILES/PSMILES ({len(df)} remaining)")

    # Done: reorder columns for bio compatibility
    cols = [
        "POLYMER_USED", "DRUG", "POLYMER_PSMILES", "DRUG_SMILES",
        "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE", "PAPER_DOI",
        "CONFIDENCE", "NOTES",
    ]
    df = df[[c for c in cols if c in df.columns]]

    # Write output files
    out_csv = OUTPUT_DIR / "training_dataset_reviewed.csv"
    df.to_csv(out_csv, index=False)
    logger.info(f"Training dataset: {len(df)} rows -> {out_csv}")

    out_drug = OUTPUT_DIR / "drug_smiles_reviewed.json"
    with open(out_drug, "w") as f:
        json.dump(drug_smiles, f, indent=2)
    logger.info(f"Drug SMILES dict -> {out_drug}")

    out_poly = OUTPUT_DIR / "polymer_psmiles_reviewed.json"
    with open(out_poly, "w") as f:
        json.dump(polymer_psmiles, f, indent=2)
    logger.info(f"Polymer PSMILES dict -> {out_poly}")

    # Stats
    print()
    print(f"{'='*60}")
    print(f"  Total rows: {len(df)}")
    print(f"  Unique drugs: {df['DRUG'].nunique()}")
    print(f"  Unique polymers: {df['POLYMER_USED'].nunique()}")
    print(f"  Unique papers (DOI): {df['PAPER_DOI'].nunique()}")
    print(f"  Confidence breakdown:")
    for conf, cnt in df["CONFIDENCE"].value_counts().items():
        print(f"    {conf:15s}: {cnt:4d}")
    print(f"{'='*60}")

    # Show drops summary
    print()
    print("Pipeline drops summary:")
    print(f"  NaN CONCENTRATION  : {before - len(df)} rows")
    # Actually tracked above differently, let's recompute
    total_input = len(df_main) + len(df_rsm)
    step1 = len(df_main) + len(df_rsm)
    step2 = step1 - (before - len(df))  # after NaN drop
    # after SMILES/PSMILES drop:
    step3 = len(df)
    print(f"  Input rows         : {total_input}")
    print(f"  After NaN conc drop: {len(df_main) + len(df_rsm) - (before - len(df))}")

    # Update the drop logs correctly
    logger.info(f"STEP 0: Input: {len(df_main)} + {len(df_rsm)} = {total_input}")
    logger.info(f"STEP 1: After NaN CONCENTRATION drop: {total_input - (before - len(df))}")


if __name__ == "__main__":
    main()
