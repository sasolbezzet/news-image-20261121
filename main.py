#!/usr/bin/env python3
"""Publish entry.png to MAKEFUN_OUTPUT_DIR, or /output when it is unset."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "entry.png"
TARGET_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    dest = TARGET_DIR / SOURCE.name
    shutil.copyfile(SOURCE, dest)
    print(f"copied {SOURCE} -> {dest}")


if __name__ == "__main__":
    main()
