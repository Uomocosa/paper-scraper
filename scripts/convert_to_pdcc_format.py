import json
import shutil
from pathlib import Path

import pandas as pd
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
HELPER_DIR = ROOT / "helper_output_dir"
REVIEW_DIR = ROOT / "claude_opus_4_8_review"

PDCC_COLS = ["POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE"]

PDCC_SPEC = {
    "pdcc_deepseek.csv": {
        "input": OUTPUT_DIR / "training_dataset_deepseek.csv",
        "description": "DeepSeek V4 Flash only",
    },
    "pdcc_kimi.csv": {
        "input": OUTPUT_DIR / "training_dataset_kimi.csv",
        "description": "Kimi K2.6 only",
    },
    "pdcc_gemma4_image.csv": {
        "input": OUTPUT_DIR / "training_dataset_gemma4_image.csv",
        "description": "Gemma4 via PDF images",
    },
    "pdcc_gemma4_text.csv": {
        "input": OUTPUT_DIR / "training_dataset_gemma4_text.csv",
        "description": "Gemma4 via PDF text",
    },
    "pdcc_deepseek_kimi_gemma.csv": {
        "input": OUTPUT_DIR / "training_dataset.csv",
        "description": "All models combined",
    },
    "pdcc_matched_deepseek_kimi.csv": {
        "input": OUTPUT_DIR / "training_dataset_matched_deepseek_kimi.csv",
        "description": "DeepSeek + Kimi agreed subset",
    },
    "pdcc_opus.csv": {
        "input": OUTPUT_DIR / "training_dataset_reviewed.csv",
        "description": "Manual review (Claude Opus 4)",
    },
}


def convert_single(src_csv: Path, dst_name: str) -> int:
    if not src_csv.exists():
        logger.warning(f"Input not found: {src_csv}")
        return 0

    df = pd.read_csv(src_csv)
    available = [c for c in PDCC_COLS if c in df.columns]

    if "PAPER_DOI" in df.columns and "SOURCE" in df.columns:
        doi = df["PAPER_DOI"].fillna("").astype(str)
        src = df["SOURCE"].fillna("").astype(str)
        combined = src.where(src != "", doi).where(src != "", doi)
        df["SOURCE"] = combined

    df_out = df[available].copy()
    dst_path = OUTPUT_DIR / dst_name
    df_out.to_csv(dst_path, index=False)
    logger.info(f"  {dst_name:35s} {len(df_out):4d} rows <- {src_csv.name}")
    return len(df_out)


def move_to_helper(patterns: list):
    for pattern in patterns:
        for f in ROOT.glob(pattern):
            dest = HELPER_DIR / f.relative_to(ROOT).parent
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest / f.name))
            logger.debug(f"  Moved {f.name} -> helper_output_dir/")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HELPER_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old pdcc_* files if they exist
    for old in OUTPUT_DIR.glob("pdcc_*.csv"):
        old.unlink()

    # Convert
    print(f"\n{'='*60}")
    print(f"  Converting to PDCC format (6 columns)")
    print(f"{'='*60}")
    total = 0
    for dst_name, spec in PDCC_SPEC.items():
        n = convert_single(spec["input"], dst_name)
        total += n
    print(f"  TOTAL: {total} rows across {len(PDCC_SPEC)} CSVs")
    print(f"{'='*60}")

    # Verify JSONs exist
    for j in ["paper_scraper_complete_smiles.json", "paper_scraper_complete_psmiles.json"]:
        p = OUTPUT_DIR / j
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            logger.info(f"  {j}: {len(data)} entries")
        else:
            logger.warning(f"  {j}: NOT FOUND")

    # Archive non-PDCC files to helper_output_dir/
    keeper = {v.rsplit("/", 1)[-1] for v in PDCC_SPEC} | {
        "paper_scraper_complete_smiles.json",
        "paper_scraper_complete_psmiles.json",
    }
    archived = 0
    for f in list(OUTPUT_DIR.iterdir()):
        if f.is_file() and f.name not in keeper:
            shutil.move(str(f), str(HELPER_DIR / f.name))
            archived += 1
    if archived:
        logger.info(f"Archived {archived} files -> {HELPER_DIR}")
    (HELPER_DIR / ".gitkeep").touch(exist_ok=True)

    print(f"\noutput/ now has {len([f for f in OUTPUT_DIR.iterdir()])} files")
    print()


if __name__ == "__main__":
    main()
