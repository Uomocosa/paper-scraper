#!/usr/bin/env python
"""Find (POLYMER_PSMILES, DRUG_SMILES) tuples shared by more than one paper.

A "conflict" here means the same polymer/drug structural pair appears in two or
more *different* papers. The same pair repeated within a single paper is not a
conflict. For each conflicting tuple the report lists the papers involved.

Usage:
    pixi run python scripts/check_psmiles_smiles_conflicts.py [INPUT_CSV]

Input  : CSV with POLYMER_PSMILES, DRUG_SMILES and PAPER columns
         (default: helper_output_dir/training_dataset.csv)
Output : psmiles_smiles_conflicts.csv
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).parent.parent
DEFAULT_INPUT = REPO_DIR / "helper_output_dir" / "training_dataset.csv"
OUTPUT_FILE = REPO_DIR / "psmiles_smiles_conflicts.csv"


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_conflicts(rows: list[dict]) -> list[dict]:
    """Group rows by (PSMILES, SMILES); return tuples spanning 2+ papers."""
    # tuple -> {paper: count}
    groups: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        psmiles = (row.get("POLYMER_PSMILES") or "").strip()
        smiles = (row.get("DRUG_SMILES") or "").strip()
        paper = (row.get("PAPER") or "").strip()
        if not psmiles or not smiles:
            continue  # incomplete tuple, nothing to compare
        groups[(psmiles, smiles)][paper] += 1

    conflicts = []
    for (psmiles, smiles), papers in groups.items():
        if len(papers) < 2:
            continue  # only one paper uses this pair -> not a conflict
        conflicts.append({
            "POLYMER_PSMILES": psmiles,
            "DRUG_SMILES": smiles,
            "NUM_PAPERS": len(papers),
            "NUM_ROWS": sum(papers.values()),
            "PAPERS": " | ".join(
                f"{p} (x{c})" for p, c in sorted(papers.items())
            ),
        })

    # Most-shared tuples first
    conflicts.sort(key=lambda c: (-c["NUM_PAPERS"], -c["NUM_ROWS"]))
    return conflicts


def check_conflicts(input_file: Path = DEFAULT_INPUT,
                    output_file: Path = OUTPUT_FILE) -> Path:
    rows = read_csv(input_file)
    if not rows:
        logger.warning(f"No data found in {input_file}")
        return output_file

    conflicts = find_conflicts(rows)

    header = ["POLYMER_PSMILES", "DRUG_SMILES", "NUM_PAPERS", "NUM_ROWS", "PAPERS"]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(conflicts)

    logger.info(f"Read {len(rows)} rows from {input_file.name}")
    if conflicts:
        logger.info(f"Found {len(conflicts)} (PSMILES, SMILES) tuples shared by 2+ papers:")
        for c in conflicts:
            logger.info(
                f"  {c['NUM_PAPERS']} papers | {c['POLYMER_PSMILES']} + "
                f"{c['DRUG_SMILES']}\n      {c['PAPERS']}"
            )
    else:
        logger.info("No tuples are shared across multiple papers.")
    logger.info(f"Output: {output_file}")
    return output_file


def test_find_conflicts():
    rows = [
        # PolyX+DrugA in two different papers -> conflict
        {"POLYMER_PSMILES": "*CC*", "DRUG_SMILES": "CCO", "PAPER": "Paper1"},
        {"POLYMER_PSMILES": "*CC*", "DRUG_SMILES": "CCO", "PAPER": "Paper2"},
        # PolyY+DrugB twice in the SAME paper -> not a conflict
        {"POLYMER_PSMILES": "*CCC*", "DRUG_SMILES": "CCN", "PAPER": "Paper3"},
        {"POLYMER_PSMILES": "*CCC*", "DRUG_SMILES": "CCN", "PAPER": "Paper3"},
        # incomplete tuple -> ignored
        {"POLYMER_PSMILES": "", "DRUG_SMILES": "CCO", "PAPER": "Paper4"},
    ]
    conflicts = find_conflicts(rows)
    assert len(conflicts) == 1, f"Expected 1 conflict, got {len(conflicts)}"
    c = conflicts[0]
    assert c["NUM_PAPERS"] == 2
    assert "Paper1" in c["PAPERS"] and "Paper2" in c["PAPERS"]
    logger.info("test_find_conflicts PASSED")


if __name__ == "__main__":
    in_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    check_conflicts(in_file)
