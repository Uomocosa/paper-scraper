#!/usr/bin/env python
"""Add quality flags to each row: polymer type, molecule type, and field presence.

Input: compiled_adsorption_data.csv
Output: classified_adsorption_data.csv (adds HAS_POLYMER, HAS_MOLECULE, HAS_WATER_PH, HAS_CONCENTRATION, HAS_CAPACITY)
"""

import csv
import re
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = REPO_DIR / "compiled_adsorption_data.csv"
OUTPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"

POLYMER_KEYWORDS = re.compile(
    r"poly|chitosan|cellulose|alginate|gelatin|dextran|"
    r"hydrogel|cryogel|aerogel|"
    r"starch|agarose|carrageenan|pectin|"
    r"copolymer|\bmer\b|acrylamid|vinylpyrrol|styrene|"
    r"urethane|imide|sulfone|"
    r"\bPVA\b|\bPAN\b|\bPEG\b|\bPCL\b|\bPLA\b|\bPET\b|\bPMMA\b|\bPPy\b|\bPANI\b",
    re.IGNORECASE,
)

NON_POLYMER_KEYWORDS = re.compile(
    r"biochar|activated carbon|charcoal|"
    r"zeolite|clay|montmorillonite|kaolinite|bentonite|"
    r"MOF|ZIF|COF|"
    r"silica|SiO2|Fe3O4|magnetite|maghemite|ferrite|"
    r"graphene|GO\b|rGO|CNT|carbon nanotube|carbon fiber|"
    r"alumina|Al2O3|TiO2|ZnO|iron oxide|"
    r"sand|soil|peat|"
    r"orange peel|rice husk|wood sawdust|"
    r"nanoparticle|nanocomposite|nanofiber",
    re.IGNORECASE,
)

GENERIC_DRUG_CLASSES = re.compile(
    r"antibiotics|antibiotic\b|"
    r"dyes?|dye mixture|"
    r"heavy\s*metal|metal ions?|metal cation|"
    r"pollutant|contaminant|"
    r"pharmaceuticals?|drugs?\b|"
    r"ions?\b|cation|anion|"
    r"organic\s*pollutant|emerging\s*pollutant|"
    r"mixture|solution|"
    r"colour|color|pigment|"
    r"herbicide|pesticide|fungicide",
    re.IGNORECASE,
)

INORGANIC_ION = re.compile(
    r"^[A-Z][a-z]?[0-9]*[+-]$|"
    r"^(arsenic|chromium|lead|cadmium|mercury|copper|zinc|nickel|"
    r"cobalt|manganese|iron|aluminum|silver|gold|platinum)\b",
    re.IGNORECASE,
)


def _clean(val: str) -> str:
    return val.strip().strip('"').strip("'")


def has_polymer(polymer_name: str) -> str:
    if not polymer_name or polymer_name.upper() == "NAN":
        return "unknown"
    name = _clean(polymer_name).lower()
    if NON_POLYMER_KEYWORDS.search(name):
        return "no"
    if POLYMER_KEYWORDS.search(name):
        return "yes"
    return "unknown"


def has_molecule(drug_name: str) -> str:
    if not drug_name or drug_name.upper() == "NAN":
        return "no"
    name = _clean(drug_name)
    if not name:
        return "no"
    if GENERIC_DRUG_CLASSES.search(name):
        return "no"
    if INORGANIC_ION.search(name):
        return "no"
    if re.match(r"^[A-Z0-9]{2,5}$", name):
        return "unknown"
    return "yes"


def _has_value(val: str) -> str:
    """Returns 'yes' if the field has a real value, 'no' if NaN/empty."""
    cleaned = _clean(val)
    return "yes" if cleaned and cleaned.upper() != "NAN" else "no"


def classify_row(row: dict) -> dict:
    hp = has_polymer(row.get("POLYMER_USED", ""))
    hm = has_molecule(row.get("DRUG", ""))
    hph = _has_value(row.get("WATER_PH", ""))
    hco = _has_value(row.get("CONCENTRATION", ""))
    hca = _has_value(row.get("CAPACITY", ""))

    return {
        "HAS_POLYMER": hp,
        "HAS_MOLECULE": hm,
        "HAS_WATER_PH": hph,
        "HAS_CONCENTRATION": hco,
        "HAS_CAPACITY": hca,
    }


def classify_all() -> Path:
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames) + [
            "HAS_POLYMER", "HAS_MOLECULE", "HAS_WATER_PH", "HAS_CONCENTRATION", "HAS_CAPACITY"
        ]

    classified = []
    for row in rows:
        row.update(classify_row(row))
        classified.append(row)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(classified)

    logger.info(f"Classified {len(classified)} rows -> {OUTPUT_FILE}")
    return OUTPUT_FILE


def test_classify():
    polymer_tests = [
        ("polyacrylamide", "yes"), ("Chitosan", "yes"), ("cellulose nanofibril", "yes"),
        ("hydrogel", "yes"), ("biochar", "no"), ("Activated carbon", "no"),
        ("Fe3O4 nanoparticles", "no"), ("graphene oxide", "no"), ("zeolite", "no"),
        ("methyl cellulose", "yes"), ("PVA", "yes"), ("", "unknown"), ("NaN", "unknown"),
    ]
    for name, expected in polymer_tests:
        result = has_polymer(name)
        assert result == expected, f"has_polymer({name!r}) = {result!r}, expected {expected!r}"
    logger.info(f"test_classify: {len(polymer_tests)} polymer tests PASSED")

    drug_tests = [
        ("Aspirin", "yes"), ("amoxicillin", "yes"), ("Methylene Blue", "yes"),
        ("Ibuprofen", "yes"), ("antibiotics", "no"), ("heavy metal", "no"),
        ("dyes", "no"), ("Cu2+", "no"), ("lead", "no"),
        ("TC", "unknown"), ("CAP", "unknown"),
        ("", "no"), ("NaN", "no"),
    ]
    for name, expected in drug_tests:
        result = has_molecule(name)
        assert result == expected, f"has_molecule({name!r}) = {result!r}, expected {expected!r}"
    logger.info(f"test_classify: {len(drug_tests)} molecule tests PASSED")
    logger.info("ALL CLASSIFY TESTS PASSED")


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        test_classify()
    else:
        classify_all()
