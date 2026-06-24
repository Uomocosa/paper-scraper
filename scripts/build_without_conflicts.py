#!/usr/bin/env python
"""Emit PDCC datasets with (PSMILES, SMILES) conflicts removed GLOBALLY.

A "conflict" is a (POLYMER_PSMILES, DRUG_SMILES) tuple that shows up under more
than one paper / model (see scripts/check_psmiles_smiles_conflicts.py). Because
the per-model CSVs are meant to be concatenated on the bio side (bio has no PAPER
column and cannot dedup itself), the dedup is done across ALL the per-model files
at once:

  For each (PSMILES, SMILES) tuple, keep it only in the BEST model's CSV, sourced
  from a single paper, and delete those rows from every other CSV.

Winner = best model (opus > deepseek > kimi > gemma), then within that model the
paper with the most rows for the tuple, ties broken by paper name. Result: each
complete tuple appears in exactly one output file under one paper, so concatenating
all the per-model outputs yields a conflict-free training set. There is no combined
output file — the user assembles it via `--pdcc-datasets <all the csvs>`.

`matched` is the deepseek∩kimi agreement subset (its rows duplicate deepseek/kimi),
so it is NOT part of the cross-model pool — it is emitted standalone, deduped only
within itself, for separate evaluation use.

Inputs : the per-model training_dataset_*.csv sources in helper_output_dir/
         (POLYMER_PSMILES, DRUG_SMILES and PAPER/PAPER_DOI).
Outputs: output_filtered/pdcc_*_without_conflicts.csv  (6-col PDCC, for bio)
         output_filtered/removed_rows_report.csv       (what was dropped + winner)
         output_filtered/*.json                        (smiles/psmiles dicts, copied)

Usage:
    pixi run python scripts/build_without_conflicts.py
"""

import csv
import shutil
from collections import defaultdict
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).parent.parent
HELPER_DIR = REPO_DIR / "helper_output_dir"
OUTPUT_DIR = REPO_DIR / "output"
OUTPUT_FILTERED_DIR = REPO_DIR / "output_filtered"
REPORT_FILE = OUTPUT_FILTERED_DIR / "removed_rows_report.csv"

# PDCC output schema (matches scripts/convert_to_pdcc_format.py).
PDCC_COLS = ["POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE"]

# Cross-model pool: (output name, source in helper_output_dir/, model tier).
# These are the real-model datasets the user concatenates. Lower tier rank = better.
POOL_SPEC = [
    ("pdcc_opus_without_conflicts.csv", "training_dataset_reviewed.csv", "opus"),
    ("pdcc_deepseek_without_conflicts.csv", "training_dataset_deepseek.csv", "deepseek"),
    ("pdcc_kimi_without_conflicts.csv", "training_dataset_kimi.csv", "kimi"),
    ("pdcc_gemma4_image_without_conflicts.csv", "training_dataset_gemma4_image.csv", "gemma"),
    ("pdcc_gemma4_text_without_conflicts.csv", "training_dataset_gemma4_text.csv", "gemma"),
]
TIER_RANK = {"opus": 0, "deepseek": 1, "kimi": 2, "gemma": 3}

# Standalone (deduped within itself only, NOT in the cross-model contest).
STANDALONE_SPEC = [
    ("pdcc_matched_deepseek_kimi_without_conflicts.csv", "training_dataset_matched_deepseek_kimi.csv"),
]

# The two name->structure dicts bio needs; copied so output_filtered/ is self-contained.
DICT_FILES = [
    "paper_scraper_complete_psmiles.json",
    "paper_scraper_complete_smiles.json",
]


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _paper_col(rows: list[dict]) -> str:
    """Return the column holding the paper identifier."""
    if rows and "PAPER" in rows[0]:
        return "PAPER"
    return "PAPER_DOI"


def _tuple(row: dict) -> tuple[str, str]:
    return ((row.get("POLYMER_PSMILES") or "").strip(),
            (row.get("DRUG_SMILES") or "").strip())


def _pick_paper(records: list[dict]) -> str:
    """Among same-tier records, pick the paper with most rows, ties by name."""
    by_paper: dict[str, int] = defaultdict(int)
    for rec in records:
        by_paper[rec["paper"]] += 1
    return min(by_paper.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def dedup_pool(sources: dict[str, tuple[Path, str]]) -> tuple[dict[str, list[dict]], list[dict]]:
    """Global cross-model dedup.

    `sources` maps output_name -> (source_path, tier). Returns
    (kept_rows_by_output, removed_report_rows). For each (PSMILES, SMILES) tuple,
    keep only the best-tier rows from one paper; drop the tuple's rows everywhere
    else. Rows with an incomplete tuple are always kept in their own file.
    """
    kept: dict[str, list[dict]] = {name: [] for name in sources}
    # tuple -> list of records {row, out, tier, paper}
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for out_name, (src, tier) in sources.items():
        rows = read_csv(src)
        pcol = _paper_col(rows)
        for row in rows:
            psmiles, smiles = _tuple(row)
            if not psmiles or not smiles:
                kept[out_name].append(row)  # incomplete -> always kept
                continue
            groups[(psmiles, smiles)].append({
                "row": row, "out": out_name, "tier": tier,
                "paper": (row.get(pcol) or "").strip(),
            })

    removed: list[dict] = []
    for (psmiles, smiles), recs in groups.items():
        best_rank = min(TIER_RANK[r["tier"]] for r in recs)
        winners = [r for r in recs if TIER_RANK[r["tier"]] == best_rank]
        win_paper = _pick_paper(winners)
        win_tier = winners[0]["tier"]

        kept_recs = [r for r in winners if r["paper"] == win_paper]
        for r in kept_recs:
            kept[r["out"]].append(r["row"])

        # Everything else for this tuple is dropped — report it grouped.
        dropped = [r for r in recs if not (r["tier"] == win_tier and r["paper"] == win_paper)]
        drop_counts: dict[tuple[str, str], int] = defaultdict(int)
        for r in dropped:
            drop_counts[(r["tier"], r["paper"])] += 1
        for (d_tier, d_paper), n in drop_counts.items():
            removed.append({
                "POLYMER_PSMILES": psmiles, "DRUG_SMILES": smiles,
                "WINNER_MODEL": win_tier, "WINNER_PAPER": win_paper,
                "DROPPED_MODEL": d_tier, "DROPPED_PAPER": d_paper,
                "ROWS_DROPPED": n,
            })

    _assert_conflict_free(kept, sources)
    return kept, removed


def _assert_conflict_free(kept: dict[str, list[dict]], sources: dict) -> None:
    """No complete tuple may appear under >1 (output, paper) across the pool."""
    seen: dict[tuple[str, str], set] = defaultdict(set)
    for out_name, rows in kept.items():
        if out_name not in sources:
            continue
        pcol = "PAPER_DOI" if "reviewed" in str(sources[out_name][0]) else "PAPER"
        for row in rows:
            psmiles, smiles = _tuple(row)
            if psmiles and smiles:
                seen[(psmiles, smiles)].add((out_name, (row.get(pcol) or "").strip()))
    offenders = {k: v for k, v in seen.items() if len(v) > 1}
    assert not offenders, f"residual cross-model/paper tuples: {offenders}"


def dedup_standalone(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Dedup a single file within itself (keep one paper per shared tuple)."""
    pcol = _paper_col(rows)
    groups: dict[tuple[str, str], dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    kept: list[dict] = []
    for row in rows:
        psmiles, smiles = _tuple(row)
        if not psmiles or not smiles:
            kept.append(row)
            continue
        groups[(psmiles, smiles)][(row.get(pcol) or "").strip()].append(row)

    removed: list[dict] = []
    for (psmiles, smiles), papers in groups.items():
        if len(papers) < 2:
            for prows in papers.values():
                kept.extend(prows)
            continue
        win = min(papers.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
        kept.extend(papers[win])
        for paper, prows in papers.items():
            if paper == win:
                continue
            removed.append({
                "POLYMER_PSMILES": psmiles, "DRUG_SMILES": smiles,
                "WINNER_MODEL": "self", "WINNER_PAPER": win,
                "DROPPED_MODEL": "self", "DROPPED_PAPER": paper,
                "ROWS_DROPPED": len(prows),
            })
    return kept, removed


def _to_pdcc(rows: list[dict]) -> list[dict]:
    """Project rows to the 6 PDCC columns, filling SOURCE from PAPER_DOI if empty."""
    out = []
    for r in rows:
        row = {c: (r.get(c) or "").strip() for c in PDCC_COLS}
        if not row["SOURCE"]:
            row["SOURCE"] = (r.get("PAPER_DOI") or "").strip()
        out.append(row)
    return out


def _write_pdcc(rows: list[dict], dst: Path) -> None:
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PDCC_COLS)
        writer.writeheader()
        writer.writerows(_to_pdcc(rows))


def build() -> Path:
    OUTPUT_FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    # Make sure no stale combined output lingers — there is intentionally none.
    stale = OUTPUT_FILTERED_DIR / "pdcc_deepseek_kimi_gemma_without_conflicts.csv"
    if stale.exists():
        stale.unlink()

    sources = {
        name: (HELPER_DIR / src, tier)
        for name, src, tier in POOL_SPEC
        if (HELPER_DIR / src).exists()
    }
    src_rows = {name: len(read_csv(path)) for name, (path, _) in sources.items()}

    kept, all_removed = dedup_pool(sources)
    for name in sources:
        _write_pdcc(kept[name], OUTPUT_FILTERED_DIR / name)
        logger.info(f"  {name:48s} {src_rows[name]:4d} -> {len(kept[name]):4d}")
    for r in all_removed:
        r["KEPT_IN"] = "(best model)"

    # Standalone files (deduped within themselves).
    for name, src in STANDALONE_SPEC:
        path = HELPER_DIR / src
        if not path.exists():
            logger.warning(f"Source not found, skipping: {path}")
            continue
        rows = read_csv(path)
        s_kept, s_removed = dedup_standalone(rows)
        _write_pdcc(s_kept, OUTPUT_FILTERED_DIR / name)
        logger.info(f"  {name:48s} {len(rows):4d} -> {len(s_kept):4d}  (standalone)")
        for r in s_removed:
            r["KEPT_IN"] = name
            all_removed.append(r)

    # Removal report
    report_cols = ["KEPT_IN", "POLYMER_PSMILES", "DRUG_SMILES",
                   "WINNER_MODEL", "WINNER_PAPER", "DROPPED_MODEL",
                   "DROPPED_PAPER", "ROWS_DROPPED"]
    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=report_cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_removed)

    # Copy name->structure dicts so output_filtered/ is a self-contained drop-in.
    for j in DICT_FILES:
        src = OUTPUT_DIR / j
        if src.exists():
            shutil.copy2(src, OUTPUT_FILTERED_DIR / j)
        else:
            logger.warning(f"Dict not found, not copied: {src}")

    logger.info(f"Removal report: {REPORT_FILE} ({len(all_removed)} entries)")
    logger.info(f"Output: {OUTPUT_FILTERED_DIR}")
    return OUTPUT_FILTERED_DIR


def test_dedup_pool_best_model_wins():
    """Same tuple in opus + deepseek -> kept only in opus; deepseek line removed."""
    import tempfile
    d = Path(tempfile.mkdtemp())
    # opus source uses PAPER_DOI; deepseek uses PAPER
    with open(d / "opus.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["POLYMER_USED", "DRUG", "POLYMER_PSMILES", "DRUG_SMILES",
                    "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE", "PAPER_DOI"])
        w.writerow(["P", "D", "*CC*", "CCO", "7", "10", "1.0", "Tab.1", "10.x/opus"])
    with open(d / "deepseek.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["POLYMER_USED", "DRUG", "POLYMER_PSMILES", "DRUG_SMILES",
                    "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE", "PAPER"])
        # same tuple, 3 rows, different paper -> all dropped (opus wins)
        for i in range(3):
            w.writerow(["P", "D", "*CC*", "CCO", "7", str(i), "2.0", "doi", "PaperB"])
        # a unique tuple -> stays
        w.writerow(["Q", "E", "*CCC*", "CCN", "6", "5", "3.0", "doi", "PaperC"])

    sources = {
        "out_opus.csv": (d / "opus.csv", "opus"),
        "out_deepseek.csv": (d / "deepseek.csv", "deepseek"),
    }
    kept, removed = dedup_pool(sources)
    assert len(kept["out_opus.csv"]) == 1
    # deepseek keeps only its unique tuple row
    ds_tuples = {_tuple(r) for r in kept["out_deepseek.csv"]}
    assert ("*CC*", "CCO") not in ds_tuples
    assert ("*CCC*", "CCN") in ds_tuples
    assert any(r["DROPPED_MODEL"] == "deepseek" and r["ROWS_DROPPED"] == 3 for r in removed)
    shutil.rmtree(d)
    logger.info("test_dedup_pool_best_model_wins PASSED")


if __name__ == "__main__":
    build()
