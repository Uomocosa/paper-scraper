#!/usr/bin/env python
"""Resolve drug SMILES and polymer PSMILES for valid classified adsorption data.

Drugs: hardcoded dict + PubChem + metal/ion patterns (no AI).
Polymers: one AI query per paper, all its polymers resolved together.

Outputs:
  output/drug_smiles.json
  output/polymer_psmiles.json
  output/resolve_smiles.log
"""

import csv
import json
import os
import re
import sys
import requests
from pathlib import Path
from collections import defaultdict

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"
OUTPUT_DIR = REPO_DIR / "output"

OPENCODE_GO_URL = "https://opencode.ai/zen/go/v1/chat/completions"
OPENCODE_GO_MODEL = "deepseek-v4-flash"

# ── Drug SMILES (manually curated + PubChem-verified) ──────────────────

SMILES_DICT = {
    'Aspirin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
    'Ibuprofen': 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
    'Indomethacin': 'CC1=C(C2=C(N1C(=O)C3=CC=C(C=C3)Cl)C=CC(=C2)OC)CC(=O)O',
    'Metoclopramide': 'CCN(CC)CCNC(=O)C1=CC(=C(C=C1OC)N)Cl',
    'Oestradiol': 'C[C@]12CC[C@H]3[C@H]([C@@H]1CC[C@@H]2O)CCC4=C3C=CC(=C4)O',
    'Pyramidone': 'CC1=C(C(=O)N(N1C)C2=CC=CC=C2)N(C)C',
    '2.4D': 'Clc1cc(Cl)ccc1OCC(=O)O',
    '2,4-D': 'Clc1cc(Cl)ccc1OCC(=O)O',
    'Ampicillin': 'CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)[C@@H](C3=CC=CC=C3)N)C(=O)O)C',
    'Doxycycline': 'C[C@@H]1[C@H]2[C@@H]([C@H]3[C@@H](C(=O)C(=C([C@]3(C(=O)C2=C(C4=C1C=CC=C4O)O)O)O)C(=O)N)N(C)C)O',
    'Fluconazole': 'C1=CC(=C(C=C1F)F)C(CN2C=NC=N2)(CN3C=NC=N3)O',
    'Lomefloxacin': 'CCN1C=C(C(=O)C2=CC(=C(C(=C21)F)N3CCNC(C3)C)F)C(=O)O',
    'Methylene Violet': 'CN(C)C1=CC2=C(C=C1)N=C3C=CC(=O)C=C3S2',
    'Piroxicam': 'CN1C(=C(C2=CC=CC=C2S1(=O)=O)O)C(=O)NC3=CC=CC=N3',
    'Thymol Blue': 'CC1=CC(=C(C=C1C2(C3=CC=CC=C3S(=O)(=O)O2)C4=CC(=C(C=C4C)O)C(C)C)C(C)C)O',
    'fluoxetine': 'CNCCC(C1=CC=CC=C1)OC2=CC=C(C=C2)C(F)(F)F',
    'propranolol': 'CC(C)NCC(COC1=CC=CC2=CC=CC=C21)O',
    'ketamine': 'CNC1(CCCCC1=O)C2=CC=CC=C2Cl',
    'atorvastatin': 'CC(C)C1=C(C(=C(N1CC[C@H](C[C@H](CC(=O)O)O)O)C2=CC=C(C=C2)F)C3=CC=CC=C3)C(=O)NC4=CC=CC=C4',
    'carbamazepine': 'C1=CC=C2C(=C1)C=CC3=CC=CC=C3N2C(=O)N',
    'diclofenac': 'C1=CC=C(C(=C1)CC(=O)O)NC2=C(C=CC=C2Cl)Cl',
    'naproxen': 'C[C@@H](C1=CC2=C(C=C1)C=C(C=C2)OC)C(=O)O',
    'Congo red': 'C1=CC=C2C(=C1)C(=CC(=C2N)N=NC3=CC=C(C=C3)C4=CC=C(C=C4)N=NC5=C(C6=CC=CC=C6C(=C5)S(=O)(=O)[O-])N)S(=O)(=O)[O-].[Na+].[Na+]',
    'Clarithromycin': 'CC[C@@H]1[C@@]([C@@H]([C@H](C(=O)[C@@H](C[C@@]([C@@H]([C@H]([C@@H]([C@H](C(=O)O1)C)O[C@H]2C[C@@]([C@H]([C@@H](O2)C)O)(C)OC)C)O[C@H]3[C@@H]([C@H](C[C@H](O3)C)N(C)C)O)(C)OC)C)C)O)(C)O',
    'Amoxicillin trihydrate': 'CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)[C@@H](C3=CC=C(C=C3)O)N)C(=O)O)C.O.O.O',
    'Sulfamethoxazole': 'CC1=CC(=NO1)NS(=O)(=O)C2=CC=C(C=C2)N',
    'Trimethoprim': 'COC1=CC(=CC(=C1OC)OC)CC2=CN=C(N=C2)N',
    'Azithromycin dihydrate': 'CC[C@@H]1[C@@]([C@@H]([C@H](N(C[C@@H](C[C@@]([C@@H]([C@H]([C@@H]([C@H](C(=O)O1)C)O[C@H]2C[C@@]([C@H]([C@@H](O2)C)O)(C)OC)C)O[C@H]3[C@@H]([C@H](C[C@H](O3)C)N(C)C)O)(C)O)C)C)C)O)(C)O.O.O',
    'Atenolol': 'CC(C)NCC(COC1=CC=C(C=C1)CC(=O)N)O',
    'Propranolol': 'CC(C)NCC(COC1=CC=CC2=CC=CC=C21)O',
    'Doxorubicin': 'C[C@H]1[C@H]([C@H](C[C@@H](O1)O[C@H]2C[C@@](CC3=C2C(=C4C(=C3O)C(=O)C5=C(C4=O)C(=CC=C5)OC)O)(C(=O)CO)O)N)O',
    'Ciprofloxacin': 'C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)N4CCNCC4)F)C(=O)O',
    'Tetracycline': 'C[C@@]1([C@H]2C[C@H]3[C@@H](C(=O)C(=C([C@]3(C(=O)C2=C(C4=C1C=CC=C4O)O)O)O)C(=O)N)N(C)C)O',
    'Metformin': 'CN(C)C(=N)N=C(N)N',
    'Ketoprofen': 'CC(C1=CC(=CC=C1)C(=O)C2=CC=CC=C2)C(=O)O',
    'Norfloxacin': 'CCN1C=C(C(=O)C2=CC(=C(C=C21)N3CCNCC3)F)C(=O)O',
    'Amoxicillin': 'CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)[C@@H](C3=CC=C(C=C3)O)N)C(=O)O)C',
    'Carbamazepine': 'C1=CC=C2C(=C1)C=CC3=CC=CC=C3N2C(=O)N',
    'Levofloxacin': 'C[C@H]1COC2=C3N1C=C(C(=O)C3=CC(=C2N4CCN(CC4)C)F)C(=O)O',
    'Acetaminophen': 'CC(=O)NC1=CC=C(C=C1)O',
    'Paracetamol': 'CC(=O)NC1=CC=C(C=C1)O',
    'Ofloxacin': 'CC1COC2=C3N1C=C(C(=O)C3=CC(=C2N4CCN(CC4)C)F)C(=O)O',
    'Chlorpyrifos': 'CCOP(=S)(OCC)OC1=NC(=C(C=C1Cl)Cl)Cl',
    'Acetylsalicylic acid': 'CC(=O)OC1=CC=CC=C1C(=O)O',
    'Cephalexin': 'CC1=C(N2[C@@H]([C@@H](C2=O)NC(=O)[C@@H](C3=CC=CC=C3)N)SC1)C(=O)O',
    'Cefotaxime': 'CC(=O)OCC1=C(N2[C@@H]([C@@H](C2=O)NC(=O)/C(=N\\OC)/C3=CSC(=N3)N)SC1)C(=O)O',
    'Chloroxylenol': 'CC1=CC(=CC(=C1Cl)C)O',
    'N,N-diethyl-meta-toluamide': 'CCN(CC)C(=O)C1=CC=CC(=C1)C',
    'Enrofloxacin': 'CCN1CCN(CC1)C2=C(C=C3C(=C2)N(C=C(C3=O)C(=O)O)C4CC4)F',
    'Metronidazole': 'CC1=NC=C(N1CCO)[N+](=O)[O-]',
    'Phenylbutazone': 'CCCCC1C(=O)N(N(C1=O)C2=CC=CC=C2)C3=CC=CC=C3',
    'Ceftiofur': 'CO/N=C(/C1=CSC(=N1)N)\\C(=O)N[C@H]2[C@@H]3N(C2=O)C(=C(CS3)CSC(=O)C4=CC=CO4)C(=O)O',
    'Prednisolone': 'C[C@]12C[C@@H]([C@H]3[C@H]([C@@H]1CC[C@@]2(C(=O)CO)O)CCC4=CC(=O)C=C[C@]34C)O',
    'Meloxicam': 'CC1=CN=C(S1)NC(=O)C2=C(C3=CC=CC=C3S(=O)(=O)N2C)O',
    'Gemfibrozil': 'CC1=CC(=C(C=C1)C)OCCCC(C)(C)C(=O)O',
    'Dorzolamide': 'CCN[C@H]1C[C@@H](S(=O)(=O)C2=C1C=C(S2)S(=O)(=O)N)C',
    'methylene blue': 'CN(C)c1ccc2c(c1)sc3cc(ccc3n2)N(C)C',
    'Methylene Blue': 'CN(C)c1ccc2c(c1)sc3cc(ccc3n2)N(C)C',
    'Methyl Orange': 'CN(C)c1ccc(cc1)N=Nc2ccc(cc2)S(=O)(=O)[O-]',
    'methyl orange': 'CN(C)c1ccc(cc1)N=Nc2ccc(cc2)S(=O)(=O)[O-]',
    'Malachite Green': 'CN(C)c1ccc(cc1)C(=C2C=CC(=[N+](C)C)C=C2)c3ccccc3',
    'malachite green': 'CN(C)c1ccc(cc1)C(=C2C=CC(=[N+](C)C)C=C2)c3ccccc3',
    'Brilliant Green': 'CC[N+](CC)(CC)c1ccc(cc1)C(=C2C=CC(=[N+](CC)CC)C=C2)c3ccccc3',
    'brilliant green': 'CC[N+](CC)(CC)c1ccc(cc1)C(=C2C=CC(=[N+](CC)CC)C=C2)c3ccccc3',
    'Rhodamine B': 'CCN(CC)c1ccc2c(c1)c(c3ccccc3o2)c4ccc(cc4)C(=O)O',
    'Crystal Violet': 'CN(C)c1ccc(cc1)C(=C2C=CC(=[N+](C)C)C=C2)c3ccc(cc3)N(C)C',
    'Safranin O': 'CC1=C(C2=CC3=CC=CC=C3N=C2C=C1N)N',
    'Neutral Red': 'CN(C)c1ccc2c(c1N)nc3ccccc3n2',
    'Phenol Red': 'c1ccc2c(c1)C(=C3C=CC(=O)C=C3OS(=O)(=O)O2)c4ccc(c(c4)O)O',
    'Bromophenol Blue': 'Brc1cc(c(Br)c(Br)c1O)C2(OS(=O)(=O)c3ccccc23)c4cc(Br)c(c(Br)c4Br)O',
    'atrazine': 'CCNc1nc(nc(n1)Cl)NC(C)C',
    'Atrazine': 'CCNc1nc(nc(n1)Cl)NC(C)C',
    'phenol': 'c1ccc(cc1)O',
    'Phenol': 'c1ccc(cc1)O',
    'bisphenol A': 'CC(C)(c1ccc(cc1)O)c2ccc(cc2)O',
    'Bisphenol A': 'CC(C)(c1ccc(cc1)O)c2ccc(cc2)O',
    'tetracycline': 'C[C@@]1([C@H]2C[C@H]3[C@@H](C(=O)C(=C([C@]3(C(=O)C2=C(C4=C1C=CC=C4O)O)O)O)C(=O)N)N(C)C)O',
    'ciprofloxacin': 'C1CC1N2C=C(C(=O)C3=CC(=C(C=C32)N4CCNCC4)F)C(=O)O',
    'amoxicillin': 'CC1([C@@H](N2[C@H](S1)[C@@H](C2=O)NC(=O)[C@@H](C3=CC=C(C=C3)O)N)C(=O)O)C',
    'ibuprofen': 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
    'diclofenac sodium': 'C1=CC=C(C(=C1)CC(=O)[O-])NC2=C(C=CC=C2Cl)Cl.[Na+]',
    'oxytetracycline': 'C[C@@]1([C@H]2C[C@H]3[C@@H](C(=O)C(=C([C@]3(C(=O)C2=C(C4=C1C=CC=C4O)O)O)O)C(=O)N)N(C)C)O',
    'ceftriaxone': 'CN(C)c1nc(sc1)C(=O)N[C@@H]2C(=O)N3C(=C(CS[C@@H]23)SC(=N)N)C(=O)O',
}
SMILES_DICT_LOWER = {k.lower(): v for k, v in SMILES_DICT.items()}

ION_PATTERNS = [
    (re.compile(r'^Cr\(VI\)$', re.I), '[Cr]'),
    (re.compile(r'^Cu\(II\)$', re.I), '[Cu+2]'),
    (re.compile(r'^Co\(II\)$', re.I), '[Co+2]'),
    (re.compile(r'^Ni\(II\)$', re.I), '[Ni+2]'),
    (re.compile(r'^Pb\(II\)$', re.I), '[Pb+2]'),
    (re.compile(r'^Hg\(II\)$', re.I), '[Hg+2]'),
    (re.compile(r'^Cd\(II\)$', re.I), '[Cd+2]'),
    (re.compile(r'^Zn\(II\)$', re.I), '[Zn+2]'),
    (re.compile(r'^Fe\(III\)$', re.I), '[Fe+3]'),
    (re.compile(r'^Mn\(II\)$', re.I), '[Mn+2]'),
    (re.compile(r'^As\(III\)$', re.I), '[As]'),
    (re.compile(r'^As\(V\)$', re.I), '[As]'),
    (re.compile(r'^Pb$', re.I), '[Pb]'),
    (re.compile(r'^Cu$', re.I), '[Cu]'),
    (re.compile(r'^Cr$', re.I), '[Cr]'),
    (re.compile(r'^Uranium$', re.I), '[U]'),
    (re.compile(r'^Arsenic$', re.I), '[As]'),
    (re.compile(r'^U\(VI\)$', re.I), '[U]'),
    (re.compile(r'^Fe$', re.I), '[Fe]'),
    (re.compile(r'^Co$', re.I), '[Co]'),
    (re.compile(r'^Ni$', re.I), '[Ni]'),
    (re.compile(r'^Zn$', re.I), '[Zn]'),
    (re.compile(r'^Mn$', re.I), '[Mn]'),
    (re.compile(r'^Hg$', re.I), '[Hg]'),
    (re.compile(r'^Cd$', re.I), '[Cd]'),
    (re.compile(r'^Eu\(III\)$', re.I), '[Eu+3]'),
    (re.compile(r'^Ag\(I\)$', re.I), '[Ag+]'),
    (re.compile(r'^Al\(III\)$', re.I), '[Al+3]'),
    (re.compile(r'^La\(III\)$', re.I), '[La+3]'),
    (re.compile(r'^Ce\(III\)$', re.I), '[Ce+3]'),
    (re.compile(r'^Sb\(III\)$', re.I), '[Sb]'),
    (re.compile(r'^Mo\(VI\)$', re.I), '[Mo]'),
    (re.compile(r'^Ti\(IV\)$', re.I), '[Ti]'),
    (re.compile(r'^Pd\(II\)$', re.I), '[Pd+2]'),
    (re.compile(r'^Pt\(IV\)$', re.I), '[Pt]'),
]

AI_PROMPT = """Paper DOI: {doi}
This paper studies adsorption and contains these polymer names:
{polymer_list}

For each polymer name, determine its correct PSMILES (repeating unit with * placeholder atoms as connection points for the polymer backbone).

ABBREVIATIONS:
CS = chitosan
PVA = poly(vinyl alcohol)
PAN = polyacrylonitrile
PPy = polypyrrole
PAA = poly(acrylic acid)
PEG = poly(ethylene glycol)
PMMA = poly(methyl methacrylate)
PET = poly(ethylene terephthalate)
PANI = polyaniline
PCL = polycaprolactone
PLA = polylactic acid
PVP = poly(vinylpyrrolidone)
PP = polypropylene
CMC = carboxymethyl cellulose
PEO = poly(ethylene oxide)
PSS = poly(styrene sulfonate)
PVDF = poly(vinylidene fluoride)
PVC = poly(vinyl chloride)

RULES:
- Output EXACTLY one line per polymer: name -> PSMILES
- PSMILES must contain exactly two * atoms as connection points
- If the name is NOT a valid polymer or you cannot determine its PSMILES:
  name -> NOT_A_VALID_POLYMER
- No explanations, no extra text

EXAMPLES OF GOOD PSMILES:
chitosan -> *C(C(C(C(C(CO)O)O)O)O)*
cellulose -> *C(C(C(C(CO)O)O)O)*
PVA -> *CC(O)*
PEG -> *CCO*
poly(acrylic acid) -> *CC(C(=O)O)*
polyaniline -> *C1=CC=C(N)C=C1*
polypyrrole -> *c1cc[nH]c1*
PAN -> *CC(C#N)*
polystyrene -> *c1ccccc1*
polyethylene -> *CC*
alginate -> *C(C(C(C(=O)[O-])O)O)*
polyacrylamide -> *CC(C(=O)N)*
chitosan (crab shells) -> *C(C(C(C(C(CO)O)O)O)O)*
calcium alginate -> *C(C(C(C(=O)[O-])O)O)*

EXAMPLES OF NOT_A_VALID_POLYMER:
activated carbon -> NOT_A_VALID_POLYMER
graphene oxide -> NOT_A_VALID_POLYMER
Fe3O4 -> NOT_A_VALID_POLYMER
biochar -> NOT_A_VALID_POLYMER
CS/PVA hydrogel -> NOT_A_VALID_POLYMER
PANI/PPy/HMS -> NOT_A_VALID_POLYMER
Ca-alginate/PDA -> NOT_A_VALID_POLYMER
PVA/CMC/GEL -> NOT_A_VALID_POLYMER
SDS-chitosan -> NOT_A_VALID_POLYMER

Now process the polymers from paper ({doi}):
{polymer_names}"""


def _clean(val):
    return val.strip().strip('"').strip("'").strip()


def _get_opencode_go_key():
    key = os.environ.get("OPENCODE_GO_KEY", "")
    if key:
        return key
    env_file = REPO_DIR.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENCODE_GO_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def _resolve_drug_pubchem(name):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name)}/property/CanonicalSMILES,ConnectivitySMILES/JSON"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            props = resp.json()["PropertyTable"]["Properties"][0]
            return props.get("CanonicalSMILES") or props.get("ConnectivitySMILES")
    except Exception:
        pass
    return None


def _resolve_drug_metal(name):
    clean = _clean(name).strip()
    for pattern, smiles in ION_PATTERNS:
        if pattern.match(clean):
            return smiles
    return None


def _resolve_polymer_via_ai(polymer_names, doi):
    key = _get_opencode_go_key()
    if not key:
        return None
    names_str = "\n".join(polymer_names)
    prompt = AI_PROMPT.format(doi=doi, polymer_list=names_str, polymer_names=names_str)
    try:
        resp = requests.post(
            OPENCODE_GO_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": OPENCODE_GO_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 8192,
                "temperature": 0.1,
            },
            timeout=300,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"] or ""
        result = {}
        for line in content.split("\n"):
            line = line.strip()
            if " -> " not in line:
                continue
            name, value = line.split(" -> ", 1)
            name = name.strip()
            value = value.strip()
            if name in polymer_names:
                result[name] = value
        for name in polymer_names:
            if name not in result:
                result[name] = "NOT_A_VALID_POLYMER"
        return result
    except Exception as e:
        logger.error(f"AI call failed for paper {doi}: {e}")
        return None


def main():
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = OUTPUT_DIR / "resolve_smiles.log"
    logger.add(log_file, rotation="10 MB")

    go_key = _get_opencode_go_key()
    if go_key:
        logger.info("OPENCODE_GO_KEY found. AI polymer resolution available.")
    else:
        logger.warning("OPENCODE_GO_KEY not found. All polymers will be NOT_A_VALID_POLYMER.")

    if not INPUT_FILE.exists():
        logger.error(f"Input file not found: {INPUT_FILE}")
        sys.exit(1)

    # ── 1. Parse and filter valid rows ──
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    logger.info(f"Loaded {len(all_rows)} rows from {INPUT_FILE}")

    valid = [r for r in all_rows
             if r.get("HAS_POLYMER") == "yes"
             and r.get("HAS_MOLECULE") == "yes"
             and r.get("HAS_WATER_PH") == "yes"
             and r.get("HAS_CONCENTRATION") == "yes"
             and r.get("HAS_CAPACITY") == "yes"]
    logger.info(f"Valid rows (all 5 fields): {len(valid)}")

    # ── 2. Collect unique drugs and (polymer, paper) pairs ──
    drug_to_papers = defaultdict(set)
    paper_to_polymers = defaultdict(set)
    for r in valid:
        drug = _clean(r.get("DRUG", "")).strip()
        poly = _clean(r.get("POLYMER_USED", "")).strip()
        doi = r.get("SOURCE", "").strip()
        if drug:
            drug_to_papers[drug].add(doi)
        if poly and doi:
            paper_to_polymers[doi].add(poly)

    logger.info(f"Unique drugs: {len(drug_to_papers)}")
    logger.info(f"Unique polymers: {sum(len(v) for v in paper_to_polymers.values())}")
    logger.info(f"Papers with polymers: {len(paper_to_polymers)}")

    # ── 3. Resolve drug SMILES (no AI) ──
    drug_smiles = {}
    drug_dict_hits = 0
    drug_pubchem_hits = 0
    drug_metal_hits = 0

    for drug_name in sorted(drug_to_papers.keys()):
        key_lower = drug_name.lower()
        if key_lower in SMILES_DICT_LOWER:
            drug_smiles[drug_name] = SMILES_DICT_LOWER[key_lower]
            drug_dict_hits += 1
            continue
        pubchem = _resolve_drug_pubchem(drug_name)
        if pubchem:
            drug_smiles[drug_name] = pubchem
            drug_pubchem_hits += 1
            continue
        metal = _resolve_drug_metal(drug_name)
        if metal:
            drug_smiles[drug_name] = metal
            drug_metal_hits += 1
            continue
        drug_smiles[drug_name] = ""

    drug_resolved = drug_dict_hits + drug_pubchem_hits + drug_metal_hits
    logger.info(f"Drug SMILES: {drug_dict_hits} dict + {drug_pubchem_hits} pubchem + {drug_metal_hits} metal = {drug_resolved}/{len(drug_to_papers)} resolved")

    # ── 4. Resolve polymer PSMILES (one AI call per paper) ──
    polymer_psmiles = {}
    ai_papers = 0
    ai_polymers = 0

    for doi, polymers in sorted(paper_to_polymers.items()):
        poly_list = sorted(polymers)
        # Skip polymers already resolved with a valid PSMILES
        unresolved = [p for p in poly_list if p not in polymer_psmiles or polymer_psmiles[p] in ("NOT_A_VALID_POLYMER", "")]
        if not unresolved:
            continue
        if not go_key:
            for p in unresolved:
                polymer_psmiles[p] = "NOT_A_VALID_POLYMER"
            continue

        logger.info(f"  Paper {ai_papers + 1}/{len(paper_to_polymers)}: {doi[:50]}... ({len(unresolved)} unresolved/{len(poly_list)} total)")
        result = _resolve_polymer_via_ai(unresolved, doi)

        if result is None:
            for p in unresolved:
                polymer_psmiles[p] = "NOT_A_VALID_POLYMER"
        else:
            for p in unresolved:
                polymer_psmiles[p] = result.get(p, "NOT_A_VALID_POLYMER")
                if polymer_psmiles[p] not in ("NOT_A_VALID_POLYMER", ""):
                    ai_polymers += 1
            ai_papers += 1

    poly_valid = sum(1 for v in polymer_psmiles.values() if v not in ("NOT_A_VALID_POLYMER", ""))
    poly_not = sum(1 for v in polymer_psmiles.values() if v == "NOT_A_VALID_POLYMER")
    logger.info(f"Polymer PSMILES: {poly_valid} valid, {poly_not} NOT_A_VALID_POLYMER, {len(polymer_psmiles)} total")
    logger.info(f"AI processed {ai_papers} papers, resolved {ai_polymers} polymers")

    # ── 5. Save outputs ──
    drug_file = OUTPUT_DIR / "drug_smiles.json"
    with open(drug_file, "w", encoding="utf-8") as f:
        json.dump(drug_smiles, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(drug_smiles)} drug SMILES to {drug_file}")

    poly_file = OUTPUT_DIR / "polymer_psmiles.json"
    with open(poly_file, "w", encoding="utf-8") as f:
        json.dump(polymer_psmiles, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(polymer_psmiles)} polymer PSMILES to {poly_file}")

    print()
    print(f"=== Summary ===")
    print(f"Drug SMILES:     {drug_resolved}/{len(drug_to_papers)} resolved ({drug_dict_hits} dict + {drug_pubchem_hits} pubchem + {drug_metal_hits} metal)")
    print(f"Polymer PSMILES: {poly_valid}/{len(polymer_psmiles)} valid, {poly_not} non-polymers")
    print(f"Drug file:  {drug_file}")
    print(f"Poly file:  {poly_file}")
    print(f"Log:        {log_file}")


if __name__ == "__main__":
    main()
