#!/usr/bin/env python3
"""
description: Declare or remove the external origins a data app may reach, in its package manifest.
last_updated: 2026-11-22

Declare (or remove) the external origins a data app may reach, in the package
manifest Tableau reads: `Packages/<package id>/manifest.json`.

Tableau serves the extension with a CSP that only allows the package's own
`content/` path. An external origin is added to that CSP only when it is BOTH
on the site's "Extension Package Allowed Origins" list (what `scaffold-data-app`
returns as `allowedOrigins`) AND requested by the package here. The site
setting alone does nothing.

The manifest field is `requestedOrigins`, and its value must be ONE
space-separated string: a JSON array is silently ignored and the CSP falls back
to package-only. `allowedOrigins` in this file is also ignored. That is why this
is a script, not a hand edit.

Safe to run at any point in a session (fresh scaffold or an already-built and
published app), and re-runnable: it merges with what the manifest already
declares, de-duplicates, and keeps any other manifest keys. Origins already in
the manifest are read leniently (case and trailing slashes are cleaned up, and
anything else is kept as-is with a warning) so one bad entry never blocks a run.
If an older workspace has no manifest, one is created from the `.trex` (id,
version, name, author).

Usage:
  python3 declare_origins.py <workspaceDir> --allowed <allowed.json> --add <origin> [<origin> ...]
  python3 declare_origins.py <workspaceDir> --remove <origin> [<origin> ...]
  python3 declare_origins.py <workspaceDir> --list

<allowed.json> is the site allow-list from a fresh `scaffold-data-app` call:
either its `allowedOrigins` array or the whole result object. Every --add origin
must be on it. `--unverified` (instead of --allowed) skips that check and warns:
the origin stays blocked until a site admin allows it.

An origin is https + host (+ optional port): `https://api.example.com`. No
path, query, or trailing slash. Tableau rejects http and wildcard (`*`) origins
at publish, and checks each origin for exact membership in the site list.

Prints the manifest path on stdout (the declared origins, one per line, for --list).
"""

import argparse
import glob
import json
import os
import re
import sys

import defusedxml.ElementTree as ET
from defusedxml import DefusedXmlException

ORIGIN_RE = re.compile(r"^https://[a-z0-9-]+(?:\.[a-z0-9-]+)*(?::\d{1,5})?$")
ADMIN_HINT = (
    "A site admin must add it under Settings > Extensions > Extension Package Allowed Origins, "
    "then re-run scaffold-data-app for the updated allowedOrigins list."
)


def die(message):
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


def warn(message):
    print(f"⚠ {message}", file=sys.stderr)


def normalize_origin(value, where):
    origin = str(value).strip()
    lowered = origin.lower()
    if not ORIGIN_RE.match(lowered):
        die(
            f'{where}: "{origin}" is not an origin. Use https + host only, e.g. https://api.example.com '
            "(no http, wildcard, path, query, or trailing slash)."
        )
    return lowered


def clean_origin(value):
    return str(value).strip().rstrip("/").lower()


def find_package(workspace):
    trexes = glob.glob(os.path.join(workspace, "Packages", "*", "extensions", "*.trex"))
    packages = sorted({os.path.dirname(os.path.dirname(t)) for t in trexes})
    if not packages:
        die(
            f"No .trex under {workspace}/Packages/*/extensions/ — is this a data-app workspace?"
        )
    if len(packages) > 1:
        die(
            "More than one package under Packages/: "
            + ", ".join(os.path.basename(p) for p in packages)
        )
    package = packages[0]
    return package, sorted(glob.glob(os.path.join(package, "extensions", "*.trex")))[0]


def local(tag):
    return tag.rsplit("}", 1)[-1]


# The manifest identity mirrors the .trex: <*-extension id extension-version>, <author name>,
# and the display name (a <resources> text when <name resource-id> is used, else <name> text).
def identity_from_trex(trex_path, package_dir):
    try:
        root = ET.parse(trex_path).getroot()
    except (ET.ParseError, DefusedXmlException) as error:
        die(f"Could not parse {trex_path}: {error}")
    ext = next((el for el in root if local(el.tag).endswith("-extension")), None)
    if ext is None:
        die(f"{trex_path} has no <worksheet-extension>/<dashboard-extension> element.")
    name = None
    name_el = next((el for el in ext if local(el.tag) == "name"), None)
    if name_el is not None:
        resource_id = name_el.get("resource-id")
        if resource_id:
            for res in root.iter():
                if local(res.tag) == "resource" and res.get("id") == resource_id:
                    text = next((t for t in res if local(t.tag) == "text"), None)
                    if text is not None and text.text:
                        name = text.text.strip()
                        break
        elif name_el.text:
            name = name_el.text.strip()
    author = next(
        (el.get("name") for el in ext if local(el.tag) == "author" and el.get("name")),
        None,
    )
    manifest = {
        "id": ext.get("id") or os.path.basename(package_dir),
        "version": ext.get("extension-version") or "1.0.0",
        "name": name or os.path.basename(package_dir),
    }
    if author:
        manifest["author"] = author
    return manifest


def read_manifest(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as error:
        die(f"Could not read/parse {path}: {error}")
    if not isinstance(manifest, dict):
        die(f"{path} must be a JSON object.")
    return manifest


def declared(manifest, path):
    value = (manifest or {}).get("requestedOrigins")
    if value is None:
        return []
    if isinstance(value, list):
        warn(
            f"{path} had requestedOrigins as a JSON array, which Tableau ignores; rewriting it as a string."
        )
        parts = value
    elif isinstance(value, str):
        parts = value.split()
    else:
        die(
            f"{path}: requestedOrigins must be a space-separated string (got {type(value).__name__})."
        )
    origins = []
    for part in parts:
        origin = clean_origin(part)
        if not ORIGIN_RE.match(origin):
            warn(
                f'{path}: requestedOrigins entry "{part}" is not a plain origin; keeping it as-is. '
                "Remove it with --remove if Tableau should not request it."
            )
            origin = str(part).strip()
        elif origin != str(part).strip():
            warn(f'{path}: rewriting requestedOrigins entry "{part}" as {origin}.')
        origins.append(origin)
    return unique(origins)


def read_allowed(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as error:
        die(f"Could not read/parse allowed-origins JSON at {path}: {error}")
    if isinstance(data, dict):
        data = data.get("allowedOrigins")
    if not isinstance(data, list):
        die(
            f"{path} must be the scaffold-data-app allowedOrigins array (or the whole result object)."
        )
    # The site list may carry trailing slashes or mixed case; compare normalized.
    return {clean_origin(o) for o in data}


def unique(seq):
    seen = []
    for item in seq:
        if item not in seen:
            seen.append(item)
    return seen


def main(argv=None):
    # argv: the arguments as a list, for callers that import this script; default: the command line.
    parser = argparse.ArgumentParser(
        prog="declare_origins.py",
        description="Declare external origins in a data-app package manifest.",
    )
    parser.add_argument("workspace")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--add", nargs="+", metavar="ORIGIN")
    action.add_argument("--remove", nargs="+", metavar="ORIGIN")
    action.add_argument("--list", action="store_true")
    check = parser.add_mutually_exclusive_group()
    check.add_argument("--allowed", metavar="ALLOWED_JSON")
    check.add_argument("--unverified", action="store_true")
    args = parser.parse_args(argv)
    if (args.allowed or args.unverified) and not args.add:
        parser.error("--allowed and --unverified only apply to --add.")

    workspace = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace):
        die(f"Workspace directory not found: {workspace}")
    package, trex = find_package(workspace)
    path = os.path.join(package, "manifest.json")
    manifest = read_manifest(path)
    current = declared(manifest, path)
    if manifest and "allowedOrigins" in manifest:
        warn(
            f'{path} has an "allowedOrigins" key, which Tableau ignores. Only requestedOrigins is read.'
        )

    if args.list:
        for origin in current:
            print(origin)
        return

    if args.add:
        adding = unique(normalize_origin(o, "--add") for o in args.add)
        if args.allowed:
            allowed = read_allowed(args.allowed)
            blocked = [o for o in adding if o not in allowed]
            if blocked:
                die(f"Not on the site allow-list: {', '.join(blocked)}. {ADMIN_HINT}")
        elif args.unverified:
            warn(
                "Skipping the site allow-list check (--unverified). Tableau keeps blocking any origin "
                "that is not also on the site allow-list. " + ADMIN_HINT
            )
        else:
            die(
                "--add needs --allowed <allowedOrigins.json> from a fresh scaffold-data-app call "
                "(or --unverified to skip the check)."
            )
        result = unique(current + adding)
    else:
        # Match on the cleaned form so a malformed stored entry can still be removed.
        removing = {clean_origin(o) for o in args.remove}
        missing = sorted(removing - {clean_origin(o) for o in current})
        if missing:
            warn("Not declared, nothing to remove: " + ", ".join(missing))
        result = [o for o in current if clean_origin(o) not in removing]

    if manifest is None:
        manifest = identity_from_trex(trex, package)
    if result:
        manifest["requestedOrigins"] = " ".join(result)
    else:
        manifest.pop("requestedOrigins", None)

    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest, indent=2) + "\n")
    print(
        f"✓ requestedOrigins: {' '.join(result) if result else '(none)'}",
        file=sys.stderr,
    )
    print(path)


if __name__ == "__main__":
    main()
