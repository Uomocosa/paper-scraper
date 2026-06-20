#!/usr/bin/env python
"""Orchestrate 5 parallel resolve_polymer_batch.py terminals.

Spawns 5 PowerShell windows, each running one partition.
Delete old part files manually before running:
  Remove-Item output/polymer_psmiles_part*.json

Usage:
  pixi run python scripts/resolve_polymer_batch_orchestrator.py
"""

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
TOTAL = 5


def main():
    import requests
    try:
        r = requests.get("http://127.0.0.1:4092/global/health", timeout=5)
        print(f"Server OK: {r.json()}\n")
    except Exception as e:
        print(f"Cannot connect to server on port 4092: {e}")
        print("Start it first: cd opencode-serve-polymers && opencode serve --port 4092 --hostname 127.0.0.1")
        sys.exit(1)

    repo_path = str(REPO_DIR)
    script_path = str(REPO_DIR / "scripts" / "resolve_polymer_batch.py")
    for part in range(TOTAL):
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-WindowStyle", "Normal",
            "-Command",
            f'Set-Location -LiteralPath "{repo_path}"; pixi run python "{script_path}" --total {TOTAL} --part {part}; Read-Host "Part {part} done. Press Enter"',
        ]
        subprocess.Popen(cmd)
        print(f"  Spawned part {part}")

    print(f"\n{TOTAL} terminals launched. Monitor each one.")
    print("After all finish:")
    print("  pixi run python scripts/merge_polymer_results.py")
    print("  pixi run python scripts/build_training_dataset.py")
    print("  pixi run python scripts/match_model_datasets.py")


if __name__ == "__main__":
    main()
