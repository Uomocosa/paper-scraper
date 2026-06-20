#!/usr/bin/env python
"""Resolve polymer PSMILES for a partition of papers via opencode serve.

Run multiple terminals in parallel with --total N --part M to split the work.
Each paper gets its own session (no context pollution).
Results saved after each paper (resume-safe).

Reads classified_adsorption_data.csv, groups polymers by paper DOI, splits
into partitions, and for each paper creates a fresh opencode session.
The agent reads CONTEXT.txt and reference_psmiles.csv for context, searches
the web for "PSMILES of <polymer>", and checks the paper PDF for SMILES.

Usage:
  pixi run python scripts/resolve_polymer_batch.py --total 5 --part 0
  pixi run python scripts/resolve_polymer_batch.py --total 5 --part 1
  ...

Requires opencode serve running on port 4092.
"""

import csv
import json
import re
import sys
import requests
from pathlib import Path
from collections import defaultdict

from loguru import logger

REPO_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = REPO_DIR / "classified_adsorption_data.csv"
OUTPUT_DIR = REPO_DIR / "output"
PDF_DIR = REPO_DIR / "OUTPUT_DIR" / "DOWNLOADED_PAPERS"
CONTEXT_FILE = REPO_DIR / "opencode-serve-polymers" / "CONTEXT.txt"
REFERENCE_FILE = REPO_DIR / "opencode-serve-polymers" / "reference_psmiles.csv"

SERVER_URL = "http://127.0.0.1:4092"
AGENT_TIMEOUT = 300

# Read context and reference files once so the prompt can reference them
_CONTEXT_TEXT = ""
_REFERENCE_TEXT = ""
try:
    _CONTEXT_TEXT = CONTEXT_FILE.read_text(encoding="utf-8")
except Exception:
    pass
try:
    _REFERENCE_TEXT = REFERENCE_FILE.read_text(encoding="utf-8")
except Exception:
    pass

AI_PROMPT = """Paper DOI: {doi}

Polymers in this paper that need PSMILES resolution:
{polymer_list}

CONTEXT (read this first):
{context_text}

REFERENCE PSMILES (check these known polymers):
{reference_text}

ABBREVIATIONS:
CS = chitosan, PVA = poly(vinyl alcohol), PAN = polyacrylonitrile, PPy = polypyrrole,
PAA = poly(acrylic acid), PEG = poly(ethylene glycol), PMMA = poly(methyl methacrylate),
PET = poly(ethylene terephthalate), PANI = polyaniline, PCL = polycaprolactone,
PLA = polylactic acid, PVP = poly(vinylpyrrolidone), PP = polypropylene,
CMC = carboxymethyl cellulose, PEO = poly(ethylene oxide), PSS = poly(styrene sulfonate),
PVDF = poly(vinylidene fluoride), PVC = poly(vinyl chloride)

INSTRUCTIONS:
1. SEARCH the web via WebFetch for "PSMILES of <polymer>" for EACH polymer name.
   Use search results as additional documentation to confirm the structure.
2. CHECK the full paper text below for any SMILES strings or structural formulas
   given by the authors.
3. USE your chemistry knowledge for well-known polymers.

OUTPUT one line per polymer: name -> PSMILES
If not a valid polymer or unknown: name -> NOT_A_VALID_POLYMER

--- FULL PAPER TEXT ---
{paper_text}
--- END ---"""


def _clean(val):
    return val.strip().strip('"').strip("'").strip()


def _extract_paper_text(paper_filename):
    """Find the matching PDF and extract all text."""
    if not paper_filename or paper_filename == ".pdf":
        return ""
    name = paper_filename.replace(".pdf", "")
    for pdf in PDF_DIR.glob(f"*{name}*.pdf"):
        if not pdf.exists():
            continue
        try:
            import pymupdf
            doc = pymupdf.open(pdf)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception:
            return ""
    return ""


def _create_session():
    resp = requests.post(f"{SERVER_URL}/session", json={}, timeout=10)
    resp.raise_for_status()
    return resp.json()["id"]


def _delete_session(session_id):
    try:
        requests.delete(f"{SERVER_URL}/session/{session_id}", timeout=5)
    except Exception:
        pass


def _send_prompt(session_id, prompt):
    resp = requests.post(
        f"{SERVER_URL}/session/{session_id}/message",
        json={
            "parts": [{"type": "text", "text": prompt}],
            "model": {"modelID": "deepseek-v4-flash", "providerID": "opencode-go"},
        },
        timeout=AGENT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _get_response_text(data):
    texts = []
    for part in data.get("parts", []):
        if part.get("type") == "text":
            texts.append(part.get("text", ""))
    return "\n".join(texts)


def _parse_response(data, expected_names):
    results = {}
    text = _get_response_text(data)
    for line in text.split("\n"):
        line = line.strip()
        if " -> " not in line:
            continue
        name, value = line.split(" -> ", 1)
        name = name.strip()
        value = value.strip()
        if name in expected_names:
            results[name] = value
    for name in expected_names:
        if name not in results:
            results[name] = "NOT_A_VALID_POLYMER"
    return results


def process_one_paper(doi, polymers, paper_name):
    """Create session, send paper with context + PDF text, parse response, delete session."""
    session_id = None
    try:
        session_id = _create_session()
        poly_list = sorted(polymers)
        paper_text = _extract_paper_text(paper_name)
        if len(paper_text) > 50000:
            paper_text = paper_text[:50000] + "\n[...truncated at 50000 chars]"

        prompt = AI_PROMPT.format(
            doi=doi,
            polymer_list="\n".join(poly_list),
            context_text=_CONTEXT_TEXT,
            reference_text=_REFERENCE_TEXT,
            paper_text=paper_text or "No PDF text available for this paper.",
        )
        data = _send_prompt(session_id, prompt)
        results = _parse_response(data, set(poly_list))
        return results
    finally:
        if session_id:
            _delete_session(session_id)


def main():
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    part = 0
    total = 1
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--part" and i + 1 < len(args):
            part = int(args[i + 1])
        elif a == "--total" and i + 1 < len(args):
            total = int(args[i + 1])
        elif a == "--test":
            try:
                r = requests.get(f"{SERVER_URL}/global/health", timeout=5)
                logger.info(f"Server OK: {r.json()}")
            except Exception as e:
                logger.error(f"Cannot connect to server: {e}")
            return

    logger.info(f"Partition {part}/{total}")

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    valid = [r for r in all_rows
             if r.get("HAS_POLYMER") == "yes"
             and r.get("HAS_MOLECULE") == "yes"
             and r.get("HAS_WATER_PH") == "yes"
             and r.get("HAS_CONCENTRATION") == "yes"
             and r.get("HAS_CAPACITY") == "yes"]
    logger.info(f"Valid rows: {len(valid)}")

    paper_polymers = defaultdict(set)
    paper_names = {}
    for r in valid:
        poly = _clean(r.get("POLYMER_USED", "")).strip()
        doi = _clean(r.get("SOURCE", "")).strip()
        pname = _clean(r.get("PAPER", "")).strip()
        if poly and doi:
            paper_polymers[doi].add(poly)
            if doi not in paper_names:
                paper_names[doi] = pname

    sorted_papers = sorted(paper_polymers.items())
    n_papers = len(sorted_papers)
    papers_per_part = n_papers // total
    remainder = n_papers % total

    start = part * papers_per_part + min(part, remainder)
    end = start + papers_per_part + (1 if part < remainder else 0)
    my_papers = sorted_papers[start:end]

    logger.info(f"Papers in partition: {len(my_papers)} (index {start}-{end-1})")

    part_file = OUTPUT_DIR / f"polymer_psmiles_part{part}.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing = {}
    if part_file.exists():
        with open(part_file, encoding="utf-8") as f:
            existing = json.load(f)
        cached = sum(1 for v in existing.values() if v not in ("NOT_A_VALID_POLYMER", ""))
        logger.info(f"Loaded {len(existing)} existing entries ({cached} valid)")

    resolved = 0
    failed = 0
    for i, (doi, polymers) in enumerate(my_papers):
        unresolved = sorted(p for p in polymers if p not in existing)
        if not unresolved:
            continue

        paper_name = paper_names.get(doi, "")
        logger.info(f"  [{i+1}/{len(my_papers)}] {doi[:50]}... ({len(unresolved)} polymers)")
        try:
            results = process_one_paper(doi, unresolved, paper_name)
            valid_count = sum(1 for v in results.values() if v not in ("NOT_A_VALID_POLYMER", ""))
            existing.update(results)
            resolved += valid_count
            logger.info(f"    -> {valid_count}/{len(unresolved)} resolved")

            with open(part_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            failed += 1
            logger.warning(f"    FAILED: {e}")

    with open(part_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    valid_total = sum(1 for v in existing.values() if v not in ("NOT_A_VALID_POLYMER", ""))
    not_total = sum(1 for v in existing.values() if v == "NOT_A_VALID_POLYMER")
    logger.info(f"Done. Part {part}: {len(my_papers)} papers, {resolved} resolved, {failed} failed")
    logger.info(f"Cumulative: {len(existing)} entries ({valid_total} valid, {not_total} non-polymers)")
    print(f"\nPart {part} done. File: {part_file}")


if __name__ == "__main__":
    main()
