import argparse
import re
import sys
import traceback
from pathlib import Path

import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem
from rdkit import RDLogger
from loguru import logger

RDLogger.DisableLog("rdApp.*")

from loguru import logger as loguru_logger
loguru_logger.disable("bio")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def fmt_val(v: str) -> str:
    return str(v).strip() if pd.notna(v) else ""


def has_range_string(val) -> bool:
    s = fmt_val(val)
    if not s or s.lower() in ("nan", "none", ""):
        return False
    return bool(re.search(r"\d+\s*[-/]\s*\d+", s))


def is_literal_nan(val) -> bool:
    s = fmt_val(val)
    return s.lower() in ("nan", "none", "")


def check_format(row: pd.Series) -> tuple:
    issues = []
    for col in ["WATER_PH", "CONCENTRATION", "CAPACITY"]:
        val = row.get(col)
        if pd.isna(val) or is_literal_nan(val):
            issues.append(f"{col}=NaN")
        elif has_range_string(val):
            issues.append(f"{col}=range({val})")
    return len(issues) == 0, "; ".join(issues) if issues else ""


def check_smiles_valid(smiles: str) -> tuple:
    if not smiles or smiles.lower() in ("nan", "none", ""):
        return False, "empty SMILES"
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "RDKit MolFromSmiles returned None"
        return True, ""
    except Exception as e:
        return False, f"RDKit exception: {e}"


def check_psmiles_valid(psmiles: str) -> tuple:
    if not psmiles or psmiles.lower() in ("nan", "none", "",
                                            "not_a_valid_polymer"):
        return False, "empty or NOT_A_VALID_POLYMER"
    try:
        from polymetrix.featurizers.polymer import Polymer
        Polymer.from_psmiles(psmiles)
        return True, ""
    except (AssertionError, ValueError) as e:
        return False, f"polymetrix rejected: {e}"
    except Exception as e:
        return False, f"polymetrix CRASH (uncaught): {e}"


def check_capping(psmiles: str, capping_atoms: dict) -> tuple:
    from bio.Bioinformatics.transform_into_smiles import transform_into_smiles
    try:
        result = transform_into_smiles(psmiles, capping_atoms)
        if not result:
            return False, "all capping atoms failed"
        return True, ""
    except Exception as e:
        return False, f"capping exception: {e}"


def check_logp(smiles: str) -> tuple:
    if not smiles or smiles.lower() in ("nan", "none", ""):
        return False, "empty SMILES"
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "MolFromSmiles failed"
        Descriptors.MolLogP(mol)
        return True, ""
    except Exception as e:
        return False, f"logP exception: {e}"


def check_fingerprint(smiles: str, radius: int = 2, nbits: int = 256) -> tuple:
    if not smiles or smiles.lower() in ("nan", "none", ""):
        return False, "empty SMILES"
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, "MolFromSmiles failed"
        AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits)
        return True, ""
    except Exception as e:
        return False, f"fingerprint exception: {e}"


def check_logd(smiles: str, ph: float, capping_atoms: dict) -> tuple:
    if not smiles or smiles.lower() in ("nan", "none", ""):
        return False, "empty SMILES"
    if pd.isna(ph):
        return False, "WATER_PH is NaN"
    try:
        from bio.Metric.calculate_logd import compute_most_probable_logd
        result = compute_most_probable_logd(
            smiles_str=smiles,
            ph_min=float(ph),
            ph_max=float(ph),
            precision=1.0,
            capping_atoms_dict=capping_atoms,
            starting_lable="logd_at_WATER_PH",
        )
        if result.empty:
            return False, "logD returned empty series"
        return True, ""
    except IndexError as e:
        return False, f"logD CRASH (protonate_smiles empty): {e}"
    except Exception as e:
        return False, f"logD exception: {e}"


def check_net_charge(smiles: str, ph: float, capping_atoms: dict) -> tuple:
    if not smiles or smiles.lower() in ("nan", "none", ""):
        return False, "empty SMILES"
    if pd.isna(ph):
        return False, "WATER_PH is NaN"
    try:
        from dimorphite_dl import protonate_smiles
        from bio.Bioinformatics.transform_into_smiles import transform_into_smiles
        valid_dict = transform_into_smiles(smiles, capping_atoms)
        if not valid_dict:
            return False, "capping failed (can't test net_charge)"
        for atom, smile in valid_dict.items():
            protonated = protonate_smiles(
                smile, ph_min=float(ph), ph_max=float(ph), precision=1.0
            )
            if len(protonated) == 0:
                return False, f"net_charge CRASH: protonate_smiles returned empty, would IndexError at line 44"
            from rdkit.Chem import rdmolops
            mol = Chem.MolFromSmiles(protonated[0])
            if mol:
                rdmolops.GetFormalCharge(mol)
        return True, ""
    except IndexError as e:
        return False, f"net_charge CRASH (protonate_smiles empty): {e}"
    except Exception as e:
        return False, f"net_charge exception: {e}"


def check_polymetrix_psmiles(psmiles: str) -> tuple:
    if not psmiles or psmiles.lower() in ("nan", "none", "",
                                            "not_a_valid_polymer"):
        return False, "empty or NOT_A_VALID_POLYMER"
    try:
        from polymetrix.featurizers.polymer import Polymer
        from polymetrix.featurizers.multiple_featurizer import MultipleFeaturizer
        from polymetrix.featurizers.sidechain_backbone_featurizer import FullPolymerFeaturizer
        from polymetrix.featurizers.chemical_featurizer import (
            NumHBondDonors, NumHBondAcceptors, NumRotatableBonds, NumRings,
            NumNonAromaticRings, NumAromaticRings, NumAtoms, TopologicalSurfaceArea,
            FractionBicyclicRings, NumAliphaticHeterocycles, SlogPVSA1, BalabanJIndex,
            MolecularWeight, Sp3CarbonCountFeaturizer, Sp2CarbonCountFeaturizer,
            MaxEStateIndex, SmrVSA5, FpDensityMorgan1, HalogenCounts, BondCounts,
            BridgingRingsCount, MaxRingSize, HeteroatomCount, HeteroatomDensity,
        )
        polymer = Polymer.from_psmiles(psmiles)
        featurizers = [
            FullPolymerFeaturizer(NumHBondDonors()),
            FullPolymerFeaturizer(NumHBondAcceptors()),
            FullPolymerFeaturizer(NumRotatableBonds()),
            FullPolymerFeaturizer(NumRings()),
            FullPolymerFeaturizer(NumNonAromaticRings()),
            FullPolymerFeaturizer(NumAromaticRings()),
            FullPolymerFeaturizer(NumAtoms()),
            FullPolymerFeaturizer(TopologicalSurfaceArea()),
            FullPolymerFeaturizer(FractionBicyclicRings()),
            FullPolymerFeaturizer(NumAliphaticHeterocycles()),
            FullPolymerFeaturizer(SlogPVSA1()),
            FullPolymerFeaturizer(BalabanJIndex()),
            FullPolymerFeaturizer(MolecularWeight()),
            FullPolymerFeaturizer(Sp3CarbonCountFeaturizer()),
            FullPolymerFeaturizer(Sp2CarbonCountFeaturizer()),
            FullPolymerFeaturizer(MaxEStateIndex()),
            FullPolymerFeaturizer(SmrVSA5()),
            FullPolymerFeaturizer(FpDensityMorgan1()),
            FullPolymerFeaturizer(HalogenCounts()),
            FullPolymerFeaturizer(BondCounts()),
            FullPolymerFeaturizer(BridgingRingsCount()),
            FullPolymerFeaturizer(MaxRingSize()),
            FullPolymerFeaturizer(HeteroatomCount()),
            FullPolymerFeaturizer(HeteroatomDensity()),
        ]
        mf = MultipleFeaturizer(featurizers)
        mf.featurize(polymer)
        return True, ""
    except Exception as e:
        return False, f"polymetrix featurization exception: {e}"


def check_polymetrix_smiles(smiles: str) -> tuple:
    if not smiles or smiles.lower() in ("nan", "none", ""):
        return False, "empty SMILES"
    try:
        from polymetrix.featurizers.molecule import Molecule, FullMolecularFeaturizer
        from polymetrix.featurizers.multiple_featurizer import MultipleFeaturizer
        from polymetrix.featurizers.chemical_featurizer import (
            NumHBondDonors, NumHBondAcceptors, NumRotatableBonds, NumRings,
            NumNonAromaticRings, NumAromaticRings, NumAtoms, TopologicalSurfaceArea,
            FractionBicyclicRings, NumAliphaticHeterocycles, SlogPVSA1, BalabanJIndex,
            MolecularWeight, Sp3CarbonCountFeaturizer, Sp2CarbonCountFeaturizer,
            MaxEStateIndex, SmrVSA5, FpDensityMorgan1, HalogenCounts, BondCounts,
            BridgingRingsCount, MaxRingSize, HeteroatomCount, HeteroatomDensity,
        )
        molecule = Molecule.from_smiles(smiles)
        featurizers = [
            FullMolecularFeaturizer(f()) for f in [
                NumHBondDonors, NumHBondAcceptors, NumRotatableBonds, NumRings,
                NumNonAromaticRings, NumAromaticRings, NumAtoms, TopologicalSurfaceArea,
                FractionBicyclicRings, NumAliphaticHeterocycles, SlogPVSA1, BalabanJIndex,
                MolecularWeight, Sp3CarbonCountFeaturizer, Sp2CarbonCountFeaturizer,
                MaxEStateIndex, SmrVSA5, FpDensityMorgan1, HalogenCounts, BondCounts,
                BridgingRingsCount, MaxRingSize, HeteroatomCount, HeteroatomDensity,
            ]
        ]
        mf = MultipleFeaturizer(featurizers)
        mf.featurize(molecule)
        return True, ""
    except Exception as e:
        return False, f"polymetrix molecule featurization exception: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Check which rows in training dataset will fail featurization."
    )
    parser.add_argument(
        "--input",
        default=OUTPUT_DIR / "training_dataset_deepseek.csv",
        help="Input CSV path",
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_DIR / "featurization_check_report.csv",
        help="Output CSV report path",
    )
    parser.add_argument(
        "--summary",
        default=OUTPUT_DIR / "featurization_check_summary.txt",
        help="Output summary text path",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    logger.info(f"Loaded {len(df)} rows from {args.input}")

    from bio.Bioinformatics.transform_into_smiles import DEFAULT_CAPPING_ATOMS

    results = []
    stage_order = [
        "FORMAT", "SMILES_VALID", "PSMILES_VALID", "CAPPING",
        "LOGP", "FINGERPRINT", "LOGD", "NET_CHARGE",
        "POLYMETRIX_PSMILES", "POLYMETRIX_SMILES"
    ]
    stage_labels = {
        "FORMAT": "Format (ranges/NaN)",
        "SMILES_VALID": "SMILES validity",
        "PSMILES_VALID": "PSMILES validity",
        "CAPPING": "PSMILES capping",
        "LOGP": "logP (RDKit)",
        "FINGERPRINT": "Fingerprint (RDKit)",
        "LOGD": "logD (dimorphite_dl)",
        "NET_CHARGE": "Net charge (dimorphite_dl)",
        "POLYMETRIX_PSMILES": "Polymetrix PSMILES feat.",
        "POLYMETRIX_SMILES": "Polymetrix SMILES feat.",
    }

    def run_stage(rec: dict, name: str, prerequisites_ok: bool, fn):
        if not prerequisites_ok:
            rec[f"{name}_OK"] = False
            rec[f"{name}_REASON"] = "SKIPPED"
            return False
        passed, reason = fn()
        rec[f"{name}_OK"] = passed
        rec[f"{name}_REASON"] = reason if reason else ""
        return passed

    for idx, row in df.iterrows():
        drug_smiles = str(row.get("DRUG_SMILES", "")).strip()
        polymer_psmiles = str(row.get("POLYMER_PSMILES", "")).strip()
        water_ph_str = str(row.get("WATER_PH", "")).strip()
        water_ph = pd.to_numeric(water_ph_str, errors="coerce")

        rec = {
            "ROW_IDX": idx,
            "PAPER": row.get("PAPER", ""),
            "DRUG": row.get("DRUG", ""),
            "POLYMER_USED": row.get("POLYMER_USED", ""),
            "DRUG_SMILES": drug_smiles[:80],
            "POLYMER_PSMILES": polymer_psmiles[:80],
            "WATER_PH": water_ph_str[:30],
            "CONCENTRATION": str(row.get("CONCENTRATION", ""))[:30],
            "CAPACITY": str(row.get("CAPACITY", ""))[:30],
        }

        # Stage 0: Format (no prerequisites)
        format_ok = run_stage(rec, "FORMAT", True,
                              lambda: check_format(row))

        # Stage 1: SMILES validity (no prerequisites)
        smiles_ok = run_stage(rec, "SMILES_VALID", True,
                              lambda: check_smiles_valid(drug_smiles))

        # Stage 2: PSMILES validity (no prerequisites)
        psmiles_ok = run_stage(rec, "PSMILES_VALID", True,
                               lambda: check_psmiles_valid(polymer_psmiles))

        # Stage 3: Capping (depends on PSMILES_VALID)
        run_stage(rec, "CAPPING", psmiles_ok,
                  lambda: check_capping(polymer_psmiles, DEFAULT_CAPPING_ATOMS))

        # Stage 4: logP (depends on SMILES_VALID)
        run_stage(rec, "LOGP", smiles_ok,
                  lambda: check_logp(drug_smiles))

        # Stage 5: Fingerprint (depends on SMILES_VALID)
        run_stage(rec, "FINGERPRINT", smiles_ok,
                  lambda: check_fingerprint(drug_smiles))

        # Stage 6: logD (depends on SMILES_VALID + format)
        run_stage(rec, "LOGD", smiles_ok and format_ok,
                  lambda: check_logd(drug_smiles, water_ph, DEFAULT_CAPPING_ATOMS))

        # Stage 7: Net charge (depends on SMILES_VALID + format)
        run_stage(rec, "NET_CHARGE", smiles_ok and format_ok,
                  lambda: check_net_charge(drug_smiles, water_ph, DEFAULT_CAPPING_ATOMS))

        # Stage 8: Polymetrix PSMILES (depends on PSMILES_VALID)
        run_stage(rec, "POLYMETRIX_PSMILES", psmiles_ok,
                  lambda: check_polymetrix_psmiles(polymer_psmiles))

        # Stage 9: Polymetrix SMILES (depends on SMILES_VALID)
        run_stage(rec, "POLYMETRIX_SMILES", smiles_ok,
                  lambda: check_polymetrix_smiles(drug_smiles))

        # Overall: all non-skipped stages must pass
        all_ok = all(
            rec.get(f"{s}_OK", False) for s in stage_order
            if rec.get(f"{s}_REASON", "") != "SKIPPED"
        )
        rec["OVERALL_OK"] = all_ok

        # First failure (excluding SKIPPED)
        fail_stage = None
        fail_reason = None
        for s in stage_order:
            if not rec.get(f"{s}_OK", False) and rec.get(f"{s}_REASON", "") != "SKIPPED":
                fail_stage = s
                fail_reason = rec.get(f"{s}_REASON", "")
                break
        rec["FAILURE_STAGE"] = fail_stage or ""
        rec["FAILURE_REASON"] = fail_reason or ""

        results.append(rec)

        if (idx + 1) % 50 == 0:
            logger.info(f"  Processed {idx + 1}/{len(df)} rows")

    report_df = pd.DataFrame(results)
    report_df.to_csv(args.output, index=False)
    logger.info(f"Report written to {args.output}")

    # Summary
    total = len(report_df)
    overall_pass = report_df["OVERALL_OK"].sum()
    overall_fail = total - overall_pass

    n_all_skipped = (report_df["FAILURE_REASON"] == "SKIPPED").sum()

    lines = [
        f"Featurization Check Summary",
        f"{'='*40}",
        f"Input: {args.input}",
        f"Total rows: {total}",
        f"OVERALL PASS: {overall_pass}",
        f"OVERALL FAIL: {overall_fail}",
        f"All skipped (no real failures): {n_all_skipped}",
        f"",
        f"Failures by stage (actual failures, not SKIPPED):",
    ]
    for st in stage_order:
        col_ok = f"{st}_OK"
        col_reason = f"{st}_REASON"
        actual_fails = report_df[(~report_df[col_ok]) & (report_df[col_reason] != "SKIPPED")]
        n_fail = len(actual_fails)
        n_executed = len(report_df[report_df[col_reason] != "SKIPPED"])
        pct = n_fail / n_executed * 100 if n_executed > 0 else 0
        label = stage_labels.get(st, st)
        lines.append(f"  {label:30s}: {n_fail:4d}/{n_executed:4d} failed ({pct:.1f}%)")

    lines.append("")
    lines.append("First failure reasons (top 20):")
    reason_counts = report_df["FAILURE_REASON"].value_counts().head(20)
    for reason, count in reason_counts.items():
        if not reason or reason == "SKIPPED":
            continue
        lines.append(f"  {count:4d}x  {reason[:120]}")

    summary_text = "\n".join(lines)
    with open(args.summary, "w") as f:
        f.write(summary_text)
    print(summary_text)


if __name__ == "__main__":
    main()
