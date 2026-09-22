#!/usr/bin/env python3
"""Validate a bilingual paper Markdown package and its local asset references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
RESIDUE_RE = re.compile(r"\b(cookie settings|sign in|subscribe|recommended articles|share this article)\b", re.I)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper_folder", type=Path)
    args = parser.parse_args()
    folder = args.paper_folder.resolve()

    errors: list[str] = []
    warnings: list[str] = []
    if not folder.is_dir():
        errors.append(f"Paper folder not found: {folder}")
        markdown_files: list[Path] = []
    else:
        markdown_files = sorted(folder.glob("*.md"))
        if len(markdown_files) < 2:
            errors.append(f"Expected English and Chinese Markdown files; found {len(markdown_files)}")
        if not (folder / "assets").is_dir():
            errors.append("Missing assets directory")

    for md_path in markdown_files:
        text = md_path.read_text(encoding="utf-8")
        if not re.search(r"^#\s+\S", text, re.M):
            errors.append(f"Missing level-1 title: {md_path.name}")
        if len(re.findall(r"^#\s+", text, re.M)) > 1:
            warnings.append(f"Multiple level-1 headings: {md_path.name}")
        if RESIDUE_RE.search(text):
            warnings.append(f"Possible website-navigation residue: {md_path.name}")
        for raw_target in IMAGE_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https"} or target.startswith("//"):
                warnings.append(f"Remote image remains in {md_path.name}: {target}")
                continue
            asset_path = (md_path.parent / unquote(target)).resolve()
            try:
                asset_path.relative_to(folder)
            except ValueError:
                warnings.append(f"Image path escapes paper folder in {md_path.name}: {target}")
                continue
            if not asset_path.is_file():
                errors.append(f"Broken image reference in {md_path.name}: {target}")

    result = {
        "folder": str(folder),
        "markdown_files": [p.name for p in markdown_files],
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "valid": not errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

