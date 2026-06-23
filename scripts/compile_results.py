#!/usr/bin/env python
"""Compile all extracted CSV data from model response directories into one file.

Scans response dirs like:
  - opencode_go_deepseek_v4_flash_max_pdf2text_responses/
  - gemma4_26b-pdf2text-respones/
  - gemma4_26b-pdf2image-respones/

Output: compiled_adsorption_data.csv in the repo root.
"""

import csv
import io
import re
from pathlib import Path

from loguru import logger

REPO_DIR = Path(__file__).parent.parent

RESPONSE_DIRS: dict[str, str] = {
    "opencode_go_deepseek_v4_flash_max_pdf2text_responses": "deepseek-v4-flash (pdf2text)",
    "gemma4_26b-pdf2text-respones": "gemma4:26b (pdf2text)",
    "gemma4_26b-pdf2image-respones": "gemma4:26b (pdf2image)",
    "review_kimi-k2_6": "kimi-k2.6 (pdf2text)",
}

OUTPUT_FILE = REPO_DIR / "compiled_adsorption_data.csv"


def parse_csv_rows(content: str, debug_label: str = "") -> list[list[str]]:
    """Parse CSV rows from a model response, skipping headers and NO USEFUL DATA.

    Handles per-page responses (pdf2image mode) where "NO USEFUL DATA" appears
    on individual pages but real CSV data may be present on other pages.
    """

    # Extract the # Response section (ignore the question text above)
    response_match = re.search(r"^# Response\s*\n(.+)$", content, re.DOTALL | re.MULTILINE)
    if not response_match:
        return []
    response_text = response_match.group(1).strip()
    if not response_text:
        return []

    rows = []
    for line in response_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Skip non-data lines (page markers, NO USEFUL DATA, markdown, bold text)
        if stripped.upper() == "NO USEFUL DATA":
            continue
        if stripped.startswith("---"):
            continue
        if stripped.startswith("```"):
            continue
        if stripped.startswith("**") or stripped.startswith("__"):
            continue

        cells = [c.strip() for c in stripped.split(",")]
        if len(cells) < 3:
            continue

        # Skip header rows
        first = cells[0].lower()
        if first in ("polymer_used", "polymer", "polymer name", "drug", "water_ph"):
            continue

        # Count non-empty, non-NaN fields in first 6 cells
        non_empty = 0
        for c in cells[:6]:
            if c and c.upper() != "NAN":
                non_empty += 1
        if non_empty < 2:
            continue

        row = [c[:200] for c in cells[:6]]
        rows.append(row)

    return rows


def compile_results() -> Path:
    """Scan all response dirs and write compiled CSV."""
    all_rows: list[list[str]] = []
    header = ["POLYMER_USED", "DRUG", "WATER_PH", "CONCENTRATION", "CAPACITY", "SOURCE", "ANALYZED_BY", "PAPER"]
    total_q_files = 0
    total_parsed_rows = 0

    for dir_name, analyzed_by in RESPONSE_DIRS.items():
        responses_dir = REPO_DIR / dir_name / "RESPONSES"
        if not responses_dir.exists():
            logger.warning(f"Directory not found: {responses_dir}")
            continue

        paper_dirs = sorted(responses_dir.iterdir())
        for paper_dir in paper_dirs:
            if not paper_dir.is_dir():
                continue
            q_file = paper_dir / "q1.md"
            if not q_file.exists():
                continue
            total_q_files += 1

            content = q_file.read_text(encoding="utf-8")
            rows = parse_csv_rows(content)
            for row in rows:
                while len(row) < 6:
                    row.append("")
                full_row = row[:6] + [analyzed_by, paper_dir.name]
                all_rows.append(full_row)
                total_parsed_rows += 1

    logger.info(f"Scanned {total_q_files} q1.md files, parsed {total_parsed_rows} CSV rows")

    # Write CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)

    logger.info(f"Compiled {len(all_rows)} data rows from {len(RESPONSE_DIRS)} model dirs")
    logger.info(f"Output: {OUTPUT_FILE}")
    return OUTPUT_FILE


def test_with_fake_response():
    """Test parse_csv_rows with mock data."""
    content = """# Question 1

...

---

# Response

CNF/GO aerogel,CAP,NaN,NaN,421.2,Scientific Reports 7 45914
Fe3O4@SiO2@mSiO2-CD,Doxycycline,3.8,100,78,10.1039/c8ra05781h
"""
    rows = parse_csv_rows(content)
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"
    assert rows[0][0] == "CNF/GO aerogel"
    assert rows[0][4] == "421.2"
    assert rows[1][1] == "Doxycycline"
    logger.info("test_with_fake_response PASSED")


def test_skips_no_useful_data():
    content = """# Question 1

...

---

# Response

NO USEFUL DATA
"""
    rows = parse_csv_rows(content)
    assert rows == [], f"Expected empty, got {rows}"
    logger.info("test_skips_no_useful_data PASSED")


def test_skips_header_rows():
    content = """# Question 1

...

---

# Response

POLYMER_USED,DRUG,WATER_PH,CONCENTRATION,CAPACITY,SOURCE
polyPhOx,Aspirin,8.20,10,0.1865,https://doi.org/10.xxx
"""
    rows = parse_csv_rows(content)
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    assert rows[0][0] == "polyPhOx"
    logger.info("test_skips_header_rows PASSED")


def test_skips_malformed_rows():
    content = """# Question 1

...

---

# Response

Some random text about the paper
Another line without commas

polyPhOx,Aspirin,8.20,10,0.1865,https://doi.org/10.xxx
"""
    rows = parse_csv_rows(content)
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    assert rows[0][0] == "polyPhOx"
    logger.info("test_skips_malformed_rows PASSED")


def test_compile_full_pipeline():
    """Integration test: write a fake response dir, compile, verify output."""
    import tempfile
    import shutil

    # Create a temp response dir matching the expected structure
    fake_dir = Path(tempfile.mkdtemp())
    fake_responses = fake_dir / "test_model_responses" / "RESPONSES"
    fake_paper = fake_responses / "Test_Paper"
    fake_paper.mkdir(parents=True)
    (fake_paper / "q1.md").write_text(
        "# Response\n\npolyPhOx,Aspirin,8.20,10,0.1865,https://doi.org/10.xxx\n",
        encoding="utf-8",
    )

    # Temporarily override RESPONSE_DIRS + REPO_DIR
    global RESPONSE_DIRS, REPO_DIR, OUTPUT_FILE
    original_dirs = RESPONSE_DIRS.copy()
    original_repo = REPO_DIR
    original_output = OUTPUT_FILE
    RESPONSE_DIRS = {"test_model_responses": "test-model (pdf2text)"}
    REPO_DIR = fake_dir
    OUTPUT_FILE = fake_dir / "compiled_adsorption_data.csv"

    try:
        out = compile_results()
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "polyPhOx" in text
        assert "test-model (pdf2text)" in text
        assert "Test_Paper" in text
        logger.info(f"test_compile_full_pipeline PASSED -> {out}")
    finally:
        RESPONSE_DIRS = original_dirs
        REPO_DIR = original_repo
        OUTPUT_FILE = original_output
        shutil.rmtree(fake_dir)


def test_usage():
    """Run a quick real compilation if response dirs exist."""
    dirs_exist = any((REPO_DIR / d).exists() for d in RESPONSE_DIRS)
    if not dirs_exist:
        logger.warning("No response directories found, skipping real compilation test")
        return
    out = compile_results()
    rows = sum(1 for _ in open(out, encoding="utf-8")) - 1  # minus header
    logger.info(f"Compiled {rows} data rows from real response dirs -> {out}")


if __name__ == "__main__":
    compile_results()
