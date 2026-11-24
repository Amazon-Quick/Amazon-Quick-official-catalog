#!/usr/bin/env python3
"""
description: Package a finalized data-app workspace into a .twbx file.
last_updated: 2026-11-22

Package a finalized data-app workspace into a `.twbx`. Workspace shape:
  <App Name>/
    <App Name>.twb
    Packages/<package id>/extensions/*.trex, content/...
    Data/...                (optional: files the .twb references)
    Resources/.agents/...   (optional: agent docs)

The archive holds the `.twb` (written first), `Packages/`, `Data/`, and
`Resources/.agents/` at its ROOT, never nested under `<App Name>/`: nesting fails
to open on publish with `PackageValidationException: Package directory contains
no extension .trex files under extensions/`.

Hard-fails unless the workspace root has exactly one `.twb`, a `Packages/` dir,
at least one `.trex` under `Packages/*/extensions/`, and every `Data/` file the
`.twb` references, or if a package `manifest.json` declares `requestedOrigins` as
anything but one space-separated string (Tableau silently ignores other shapes).

Warns (never fails) about things that break or leak at runtime: external origins
referenced in content/ but not declared with declare_origins.py, fetch() of
package-relative paths (fails in the null-origin sandbox), and secret-looking
keys in any file that gets packaged (hidden files are skipped, so never shipped).
In minified or bundled files, only origins used as a request target (fetch,
src/href, url(), import, WebSocket, ...) or written as a bare origin string (an
API base URL) count, so library doc links in a React or esbuild bundle don't
trip the warning.

Output defaults to `<App Name>.twbx` next to the workspace dir; an existing
file is overwritten. Prints the output path on stdout.

Usage: python3 package_twbx.py <workspaceDir> [outputPath]
"""

import glob
import json
import os
import re
import sys
import zipfile

import defusedxml.ElementTree as ET
from defusedxml import DefusedXmlException

PACKED_DIRS = ("Packages", "Data", "Resources/.agents")

FILE_PATH_ATTRS = ("filename", "dbname")

ORIGIN_IN_CODE = re.compile(r"""https?://[A-Za-z0-9.-]+(?::\d+)?""")
# Namespace URIs and other identifiers that never become network requests.
NON_NETWORK_ORIGINS = {"http://www.w3.org", "https://www.w3.org"}
# The same origin used as a request target; the only kind counted in bundled code.
NETWORK_ORIGIN = re.compile(
    r"""(?:fetch\(|new\s+(?:WebSocket|EventSource|Worker)\(|\.open\(\s*['"]\w+['"]\s*,|"""
    r"""\b(?:src|href|action|baseURL|baseUrl)\s*[:=]|url\(|@import|\bfrom|import\()\s*['"`]?"""
    r"""(https?://[A-Za-z0-9.-]+(?::\d+)?)"""
)
# A string literal that is just an origin, like an API base URL (`const API = 'https://…'`).
BARE_ORIGIN = re.compile(r"""['"`](https?://[A-Za-z0-9.-]+(?::\d+)?)/?['"`]""")
# A package-relative fetch; skips URLs with a scheme and template literals that start with `${…}`.
RELATIVE_FETCH = re.compile(
    r"""fetch\(\s*(?:['"](?![A-Za-z][A-Za-z0-9+.-]*:)|`(?!\$\{|[A-Za-z][A-Za-z0-9+.-]*:))"""
)
# A secret-looking key assigned a long string literal (e.g. "SPOTIFY_CLIENT_SECRET": "…"), not `token = null`.
SECRET_KEY = re.compile(
    r"""[\w-]*(?:secret|token|api[_-]?key|password|passwd|private[_-]?key)['"]?\s*[:=]\s*['"]([^'"\s]{8,})['"]""",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(
    r"placeholder|example|changeme|replace|dummy|sample|your[_-]|xxxx|\*\*\*\*|^<.*>$",
    re.IGNORECASE,
)
CODE_EXTENSIONS = (".js", ".mjs", ".html", ".htm", ".css")
BINARY_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".zip",
    ".hyper",
    ".pdf",
    ".mp3",
    ".mp4",
    ".wasm",
)
MINIFIED_LINE = 1000


def die(message):
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


def collect_entries(workspace, top, allowed=None):
    entries = []  # (path, archive name, is_dir)
    for root, dirs, files in os.walk(os.path.join(workspace, top)):
        dirs[:] = sorted(
            name for name in dirs if not name.startswith((".", "__MACOSX"))
        )
        rel_root = os.path.relpath(root, workspace).replace(os.sep, "/")
        entries.append((root, rel_root, True))
        for name in sorted(files):
            rel = f"{rel_root}/{name}"
            if name.startswith(".") or (allowed is not None and rel not in allowed):
                continue
            entries.append((os.path.join(root, name), rel, False))

    ancestor_dirs = {
        rel.rsplit("/", i)[0]
        for _, rel, is_dir in entries
        if not is_dir
        for i in range(1, rel.count("/") + 1)
    }
    return [
        (path, rel)
        for path, rel, is_dir in entries
        if not is_dir or rel in ancestor_dirs
    ]


def referenced_data_files(workspace, twb):
    try:
        root = ET.parse(os.path.join(workspace, twb)).getroot()
    except (ET.ParseError, DefusedXmlException) as error:
        die(f"Could not parse {twb}: {error}")
    referenced = set()
    for element in root.iter("connection"):
        directory = element.get("directory", "").replace("\\", "/").rstrip("/")
        for attr in FILE_PATH_ATTRS:
            path = element.get(attr, "").replace("\\", "/")
            if attr == "filename" and directory and path:
                path = f"{directory}/{path}"
            if path.startswith("Data/"):
                referenced.add(path)
    return referenced


def collect_packed_dirs(workspace, twb):
    referenced = referenced_data_files(workspace, twb)
    entries_by_top = {}
    for top in PACKED_DIRS:
        if os.path.isdir(os.path.join(workspace, top)):
            entries = collect_entries(
                workspace, top, referenced if top == "Data" else None
            )
            if entries:
                entries_by_top[top] = entries

    packed = {rel for entries in entries_by_top.values() for _, rel in entries}
    missing = sorted(referenced - packed)
    if missing:
        die(
            f"{twb} references files missing from the workspace (no data at runtime): "
            + ", ".join(missing)
        )
    return entries_by_top


def warn(message):
    print(f"⚠ {message}", file=sys.stderr)


def requested_origins(package_dir):
    path = os.path.join(package_dir, "manifest.json")
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as error:
        die(f"Could not read/parse {path}: {error}")
    value = manifest.get("requestedOrigins") if isinstance(manifest, dict) else None
    if value is None:
        return set()
    if not isinstance(value, str):
        die(
            f"{path}: requestedOrigins must be ONE space-separated string; Tableau ignores a "
            f"{type(value).__name__} and blocks every external origin. Fix it with declare_origins.py."
        )
    return {o.lower() for o in value.split()}


def read_text(path):
    with open(path, "rb") as f:
        data = f.read()
    return None if b"\0" in data[:8192] else data.decode("utf-8", errors="replace")


def has_secret(text):
    return any(not PLACEHOLDER.search(value) for value in SECRET_KEY.findall(text))


def is_bundled(name, text):
    return ".min." in name or any(
        len(line) > MINIFIED_LINE for line in text.splitlines()
    )


# Runtime problems a zip can't catch: undeclared external origins and leaked secrets.
# Checks exactly the Packages/ files that go into the .twbx.
def preflight(workspace, entries):
    by_package = {}
    for path, rel in entries:
        parts = rel.split("/")
        if len(parts) > 2 and os.path.isfile(path):
            by_package.setdefault(parts[1], []).append((path, parts))
    for pkg, files in sorted(by_package.items()):
        declared = requested_origins(os.path.join(workspace, "Packages", pkg))
        undeclared, relative_fetch, flagged_files = {}, [], []
        for path, parts in files:
            name, rel = parts[-1], "/".join(parts[1:])
            in_content = parts[2] == "content"
            # The vendored Extensions API library is Tableau's own code.
            if name.startswith("tableau.extensions.") or name.lower().endswith(
                BINARY_EXTENSIONS
            ):
                continue
            text = read_text(path)
            if text is None:
                continue
            if has_secret(text):
                flagged_files.append(rel)
            if not in_content or not name.endswith(CODE_EXTENSIONS):
                continue
            if is_bundled(name, text):
                found = NETWORK_ORIGIN.findall(text) + BARE_ORIGIN.findall(text)
            else:
                found = ORIGIN_IN_CODE.findall(text)
            for origin in found:
                origin = origin.lower()
                if origin not in declared and origin not in NON_NETWORK_ORIGINS:
                    undeclared.setdefault(origin, rel)
            if RELATIVE_FETCH.search(text):
                relative_fetch.append(rel)
        if undeclared:
            warn(
                f"{pkg}: content references origins not in requestedOrigins: "
                + ", ".join(f"{o} ({f})" for o, f in sorted(undeclared.items()))
                + ". Requests, images, scripts, or styles from them are blocked by the CSP unless declared "
                "with declare_origins.py (plain links that only navigate are fine)."
            )
        if relative_fetch:
            warn(
                f"{pkg}: fetch() of a package-relative path in {', '.join(relative_fetch)} fails in the "
                "sandbox (null origin, no CORS). Ship data/config as a .js file loaded with <script src>."
            )
        if flagged_files:
            warn(
                f"{pkg}: secret-looking keys in {', '.join(flagged_files)}. Anyone who can open or download "
                "the workbook can read them; see Security best practices in SKILL.md."
            )


def main(argv=None):
    # argv: the arguments as a list, for callers that import this script; default: the command line.
    argv = sys.argv if argv is None else ["package_twbx.py", *argv]
    if len(argv) < 2 or len(argv) > 3:
        die("Usage: python3 package_twbx.py <workspaceDir> [outputPath]")

    workspace = os.path.abspath(argv[1])
    if not os.path.isdir(workspace):
        die(f"Workspace directory not found: {workspace}")

    twbs = sorted(
        name
        for name in os.listdir(workspace)
        if name.endswith(".twb") and os.path.isfile(os.path.join(workspace, name))
    )
    if len(twbs) != 1:
        die(
            f"Expected exactly one .twb at the workspace root, found {len(twbs)}: {workspace}"
        )
    twb = twbs[0]

    packages = os.path.join(workspace, "Packages")
    if not os.path.isdir(packages):
        die(f"Missing Packages/ directory in {workspace}")

    if not glob.glob(os.path.join(packages, "*", "extensions", "*.trex")):
        die(
            "No .trex under Packages/*/extensions/ — publish would fail with "
            '"Package directory contains no extension .trex files under extensions/".'
        )

    output = (
        os.path.abspath(argv[2])
        if len(argv) == 3
        else os.path.join(
            os.path.dirname(workspace), os.path.basename(workspace) + ".twbx"
        )
    )

    entries_by_top = collect_packed_dirs(workspace, twb)
    preflight(workspace, entries_by_top.get("Packages", []))

    # Paths are workspace-relative so nothing lands under an <App Name>/ prefix.
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(os.path.join(workspace, twb), twb)
        for entries in entries_by_top.values():
            for path, rel in entries:
                archive.write(path, rel)

    print(
        f"✓ Packaged {twb} + {', '.join(top + '/' for top in entries_by_top)} into {output}",
        file=sys.stderr,
    )
    print(output)


if __name__ == "__main__":
    main()
