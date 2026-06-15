"""
Load retrospective type metadata from reference files.

Scans references/{category}/*.md and extracts the <Metadata> block
from each file. Returns a list of dicts ready for routing.

Usage:
    from scripts.load_retro_index import load_index
    index = load_index()
    # Filter by category
    agile = [r for r in index if r['category'] == 'agile']
    # Filter by team size
    small = [r for r in index if r['max_team_size'] <= 8]

Returns:
    list[dict] with keys: name, category, aliases, duration, team_size,
    best_for, definition, path
"""

import json
import os
import re

CATEGORIES = [
    "agile",
    "incident",
    "project",
    "strategic",
    "team-health",
    "personal",
    "ai-agent",
]


def parse_metadata_block(content):
    """Extract fields from a <Metadata> XML block in a reference doc."""
    match = re.search(r"<Metadata>(.*?)</Metadata>", content, re.DOTALL)
    if not match:
        return None

    block = match.group(1)
    metadata = {}

    # Parse key: value pairs
    for line in block.strip().splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip().lower().replace(" ", "_")] = value.strip()

    return metadata


def load_index(references_dir=None):
    """
    Load the full retro index by scanning all reference files.

    Args:
        references_dir: Path to the references/ directory.
                       If None, auto-resolves relative to this script.

    Returns:
        list[dict]: One entry per retrospective type with routing metadata.
    """
    if references_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        references_dir = os.path.join(os.path.dirname(script_dir), "references")

    index = []

    for category in CATEGORIES:
        cat_path = os.path.join(references_dir, category)
        if not os.path.isdir(cat_path):
            continue

        for fname in sorted(os.listdir(cat_path)):
            if not fname.endswith(".md"):
                continue
            # Sanitize: reject any filename with path separators or traversal
            if os.sep in fname or "/" in fname or ".." in fname:
                continue

            fpath = os.path.join(cat_path, fname)
            fpath = os.path.realpath(fpath)
            if not fpath.startswith(os.path.realpath(references_dir)):
                continue
            with open(fpath, encoding="utf-8") as f:
                content = f.read(2000)  # Metadata is always in the first 2KB

            metadata = parse_metadata_block(content)
            if metadata is None:
                continue

            entry = {
                "name": metadata.get("name", fname.replace(".md", "")),
                "category": category,
                "aliases": metadata.get("aliases", ""),
                "duration": metadata.get("duration", ""),
                "team_size": metadata.get("team_size", ""),
                "best_for": metadata.get("best_for", ""),
                "definition": metadata.get("definition", ""),
                "path": f"references/{category}/{fname}",
            }
            index.append(entry)

    return index


def filter_by_category(index, category):
    """Filter index entries by category."""
    return [r for r in index if r["category"] == category]


def search_index(index, query):
    """Simple text search across name, aliases, best_for, definition."""
    query_lower = query.lower()
    results = []
    for entry in index:
        searchable = " ".join(
            [
                entry.get("name", ""),
                entry.get("aliases", ""),
                entry.get("best_for", ""),
                entry.get("definition", ""),
            ]
        ).lower()
        if query_lower in searchable:
            results.append(entry)
    return results


if __name__ == "__main__":
    index = load_index()
    print(
        f"Loaded {len(index)} retrospective types across {len(CATEGORIES)} categories"
    )
    print(json.dumps(index[:3], indent=2))
