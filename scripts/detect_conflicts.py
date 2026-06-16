#!/usr/bin/env python
"""Detect papers analyzed by multiple models and report conflicting values.

Input: compiled_adsorption_data.csv
Output: conflicts_report.csv (papers analyzed by 2+ models, with value comparison)
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).parent.parent
INPUT_FILE = REPO_DIR / "compiled_adsorption_data.csv"
OUTPUT_FILE = REPO_DIR / "conflicts_report.csv"


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def detect_conflicts() -> Path:
    rows = read_csv(INPUT_FILE)
    if not rows:
        logger.warning(f"No data found in {INPUT_FILE}")
        return OUTPUT_FILE

    # Group by (paper, polymer, drug, pH, concentration)
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        paper = row.get("PAPER", "").strip()
        polymer = row.get("POLYMER_USED", "").strip()
        drug = row.get("DRUG", "").strip()
        ph = row.get("WATER_PH", "").strip()
        conc = row.get("CONCENTRATION", "").strip()
        key = f"{paper}||{polymer}||{drug}||{ph}||{conc}"
        groups[key].append(row)

    conflicts = []
    for key, group in groups.items():
        analyzers = set(r.get("ANALYZED_BY", "") for r in group)
        if len(analyzers) < 2:
            continue

        paper = group[0].get("PAPER", "")
        polymer = group[0].get("POLYMER_USED", "")
        drug = group[0].get("DRUG", "")
        ph = group[0].get("WATER_PH", "")
        conc = group[0].get("CONCENTRATION", "")

        # Collect capacities per analyzer
        caps: dict[str, list[str]] = defaultdict(list)
        for r in group:
            analyzer = r.get("ANALYZED_BY", "")
            cap = r.get("CAPACITY", "").strip()
            if cap and cap.upper() != "NAN":
                caps[analyzer].append(cap)

        if len(caps) < 2:
            continue

        # For each pair of analyzers, compare
        analyzers_list = sorted(caps.keys())
        for i in range(len(analyzers_list)):
            for j in range(i + 1, len(analyzers_list)):
                a1 = analyzers_list[i]
                a2 = analyzers_list[j]
                # Compare value by value (assume same order)
                for c1, c2 in zip(caps[a1], caps[a2]):
                    try:
                        v1 = float(c1)
                        v2 = float(c2)
                        diff = abs(v1 - v2)
                        diff_pct = (diff / max(abs(v1), abs(v2), 0.001)) * 100
                        verdict = "AGREE" if diff_pct < 10 else "DISAGREE"
                    except ValueError:
                        v1_str = c1
                        v2_str = c2
                        diff_pct = 100 if v1_str != v2_str else 0
                        verdict = "AGREE" if v1_str == v2_str else "DISAGREE"

                    conflicts.append({
                        "PAPER": paper,
                        "POLYMER_USED": polymer,
                        "DRUG": drug,
                        "WATER_PH": ph,
                        "CONCENTRATION": conc,
                        f"{a1}_CAPACITY": c1,
                        f"{a2}_CAPACITY": c2,
                        "DIFF_PERCENT": f"{diff_pct:.1f}",
                        "VERDICT": verdict,
                    })

    header = ["PAPER", "POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION",
              "ANALYZER_1", "CAPACITY_1", "ANALYZER_2", "CAPACITY_2", "DIFF_PERCENT", "VERDICT"]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for c in conflicts:
            a1, a2 = sorted(caps.keys())
            writer.writerow([
                c["PAPER"], c["POLYMER_USED"], c["DRUG"], c["WATER_PH"], c["CONCENTRATION"],
                a1, c.get(f"{a1}_CAPACITY", ""),
                a2, c.get(f"{a2}_CAPACITY", ""),
                c["DIFF_PERCENT"], c["VERDICT"],
            ])

    logger.info(f"Found {len(conflicts)} conflicting data points")
    logger.info(f"Output: {OUTPUT_FILE}")
    return OUTPUT_FILE


def test_with_fake_data():
    import tempfile
    import shutil

    fake_dir = Path(tempfile.mkdtemp())
    fake_csv = fake_dir / "compiled_adsorption_data.csv"
    with open(fake_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE", "ANALYZED_BY", "PAPER"])
        w.writerow(["PolyX", "Aspirin", "7.0", "10", "0.5", "doi", "deepseek-v4-flash (pdf2text)", "Paper1"])
        w.writerow(["PolyX", "Aspirin", "7.0", "10", "0.5", "doi", "gemma4:26b (pdf2text)", "Paper1"])
        w.writerow(["PolyY", "DrugA", "6.0", "25", "100", "doi", "deepseek-v4-flash (pdf2text)", "Paper2"])

    global INPUT_FILE, OUTPUT_FILE
    original_in = INPUT_FILE
    original_out = OUTPUT_FILE
    # Override for test
    import scripts.detect_conflicts as mod
    mod.INPUT_FILE = fake_csv
    mod.OUTPUT_FILE = fake_dir / "conflicts_report.csv"

    try:
        out = detect_conflicts()
        rows = list(csv.DictReader(open(out, encoding="utf-8")))
        assert len(rows) == 1, f"Expected 1 conflict, got {len(rows)}"
        assert rows[0]["VERDICT"] == "AGREE"
        logger.info("test_with_fake_data PASSED")
    finally:
        mod.INPUT_FILE = original_in
        mod.OUTPUT_FILE = original_out
        shutil.rmtree(fake_dir)


def test_usage():
    if not INPUT_FILE.exists():
        logger.warning(f"No input file at {INPUT_FILE}, skipping")
        return
    out = detect_conflicts()
    rows = sum(1 for _ in open(out, encoding="utf-8")) - 1
    logger.info(f"Found {rows} conflicts")


if __name__ == "__main__":
    detect_conflicts()
