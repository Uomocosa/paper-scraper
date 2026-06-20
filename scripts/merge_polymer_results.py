#!/usr/bin/env python
"""Merge all polymer_psmiles_part*.json files into one polymer_psmiles.json.

Validates each PSMILES using lele-bioinformatics' is_psmiles_string_valid
(polymetrix + RDKit). Strips backtick formatting before validation.
Invalid entries are flagged as NOT_A_VALID_POLYMER.

Usage:  pixi run python scripts/merge_polymer_results.py
"""

import json
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "polymer_psmiles.json"
REPO_DIR = OUTPUT_DIR.parent
LELE_BIO_DIR = REPO_DIR.parent / "lele-py-bioinformatics"

sys.path.insert(0, str(LELE_BIO_DIR))
from bio.Bioinformatics import is_psmiles_string_valid


def _clean_psmiles(val: str) -> str | None:
    """Strip markdown formatting and validate. Returns cleaned PSMILES or None."""
    val = val.strip().strip("`").strip()
    if not val or val.upper() in ("NOT_A_VALID_POLYMER", ""):
        return None
    if not is_psmiles_string_valid(val):
        return None
    return val


def main():
    part_files = sorted(OUTPUT_DIR.glob("polymer_psmiles_part*.json"))
    if not part_files:
        print("No part files found in output/")
        return

    total_entries = {}
    for pf in part_files:
        with open(pf, encoding="utf-8") as f:
            data = json.load(f)
        total_entries.update(data)
        print(f"  {pf.name}: {len(data)} entries")

    print(f"\nLoaded {len(total_entries)} unique entries. Validating...")

    validated = {}
    cleaned = {}
    invalid_count = 0
    for name, psmiles in total_entries.items():
        if psmiles == "NOT_A_VALID_POLYMER":
            validated[name] = "NOT_A_VALID_POLYMER"
            continue
        cleaned_psmiles = _clean_psmiles(psmiles)
        if cleaned_psmiles:
            validated[name] = cleaned_psmiles
            if cleaned_psmiles != psmiles:
                cleaned[name] = (psmiles, cleaned_psmiles)
        else:
            validated[name] = "NOT_A_VALID_POLYMER"
            invalid_count += 1
            print(f"  REJECTED: {name} -> {psmiles}")

    if cleaned:
        print(f"\nFormatted (backticks stripped):")
        for name, (orig, clean) in sorted(cleaned.items()):
            print(f"  {name}: {orig} -> {clean}")

    valid_count = sum(1 for v in validated.values() if v not in ("NOT_A_VALID_POLYMER", ""))
    not_count = sum(1 for v in validated.values() if v == "NOT_A_VALID_POLYMER")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(validated, f, indent=2, ensure_ascii=False)

    print(f"\n=== Validation Results ===")
    print(f"Total entries: {len(validated)}")
    print(f"Valid PSMILES: {valid_count}")
    print(f"Non-polymers:  {not_count}")
    if invalid_count:
        print(f"Rejected (invalid format): {invalid_count}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
