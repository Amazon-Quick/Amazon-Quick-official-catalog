"""Macros module for dynamic catalog generation.

Reads catalog.json for categorization and asset type, then pulls
display data from each asset's SKILL.md frontmatter.
"""

import json
import re
from pathlib import Path

import yaml
from pydantic import BaseModel

REPO_URL = "https://github.com/Amazon-Quick/amazon-quick-official-marketplace"


class AssetEntry(BaseModel):
    path: str
    type: str
    name: str = ""
    display_name: str = ""
    icon: str = ""
    description: str = ""
    depends_on: list[str] = []
    last_updated: str = "—"

    @property
    def label(self) -> str:
        return self.display_name or self.name


class Category(BaseModel):
    name: str
    assets: list[AssetEntry] = []


def define_env(env):
    @env.macro
    def skill_catalog() -> str:
        project_dir = Path(__file__).resolve().parent.parent
        catalog_path = project_dir / "catalog.json"

        if not catalog_path.exists():
            return "_No catalog found._"

        catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        categories = _build_categories(project_dir, catalog_data)

        if not categories:
            return "_No assets found._"

        sections = []
        for cat in categories:
            lines = [
                f"### {cat.name}\n",
                "| Name | Type | Description | Integrations | Updated |",
                "|------|------|-------------|--------------|---------|",
            ]
            for a in cat.assets:
                desc = _truncate(a.description, 100)
                deps = ", ".join(a.depends_on) or "—"
                dl_url = f"{REPO_URL}/tree/main/{a.path}"
                lines.append(
                    f"| {a.icon} [{a.label}]({dl_url}) | {a.type.capitalize()} | {desc} | {deps} | {a.last_updated} |"
                )
            sections.append("\n".join(lines))

        return "\n\n".join(sections)


def _build_categories(project_dir: Path, catalog_data: dict) -> list[Category]:
    categories = []
    for cat_data in catalog_data.get("categories", []):
        entries = []
        for asset in cat_data.get("assets", []):
            asset_path = project_dir / asset["path"]
            skill_file = asset_path / "SKILL.md"
            frontmatter = _parse_frontmatter(skill_file) if skill_file.exists() else {}
            entries.append(
                AssetEntry(
                    path=asset["path"],
                    type=asset["type"],
                    name=frontmatter.get("name", asset_path.name),
                    display_name=frontmatter.get("display_name", ""),
                    icon=frontmatter.get("icon", ""),
                    description=frontmatter.get("description", ""),
                    depends_on=frontmatter.get("depends-on", []),
                    last_updated=frontmatter.get("last_updated", "—"),
                )
            )
        if entries:
            categories.append(Category(name=cat_data["name"], assets=entries))
    return categories


def _parse_frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^(?:---|\_{3,})\s*\n(.+?)\n(?:---|\_{3,})", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _truncate(text: str, length: int) -> str:
    text = text.replace("|", "\\|").replace("\n", " ")
    if len(text) <= length:
        return text
    return text[: length - 1] + "…"
