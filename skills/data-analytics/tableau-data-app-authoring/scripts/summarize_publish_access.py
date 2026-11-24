#!/usr/bin/env python3
"""
description: Turn a publish-workbook result into the exact message shown to the user.
last_updated: 2026-11-22

Turn a `publish-workbook` result into the exact message shown to the user.

Input: the result JSON ({ status, data, url, warnings, permissions?, permissionsNote? }).
`permissions` is the workbook's GranteeCapability[] rules:
  [{ user?|group?: { id, name? }, capabilities?: { capability?: [{ name, mode }] } }]
Present only for a project publish whose rules were read; `permissionsNote` only
when that read failed (never printed, and wins over `permissions`); both absent
for Personal Space, which prints the confirmation only.

Viewers need Read (View), Connect (Full Data Query) and VizqlDataApiAccess
(API Access), each with mode exactly Allow and no Deny. Each rule lacking any of
them is listed by grantee name (never id) with its missing capabilities.

Usage: python3 summarize_publish_access.py <result.json> [--published-datasource [NAME]]...
  Pass --published-datasource only when the app uses a published data source;
  repeat it once per data source when the app uses several.
Exits nonzero unless status is "published"; surface errors/warnings verbatim then.
"""

import json
import sys

REQUIRED_CAPABILITIES = [
    ("Read", "View"),
    ("Connect", "Full Data Query"),
    ("VizqlDataApiAccess", "API Access"),
]

MISSING_HEADER = (
    "Some viewers may not be able to view this data app. Missing workbook permissions:"
)
NO_RULES = (
    "No permission rules were returned for this workbook. "
    "Viewers need View, Full Data Query, and API Access on the workbook."
)
NOT_VERIFIED = "Viewer access was not verified. Viewers need View, Full Data Query, and API Access on the workbook."
USAGE = "Usage: python3 summarize_publish_access.py <result.json> [--published-datasource [NAME]]..."


def die(message):
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


def parse_args(argv):
    path = None
    sources = None  # None = option absent, [] = unnamed only, else the distinct names
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--published-datasource":
            if sources is None:
                sources = []
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                i += 1
                if argv[i] and argv[i] not in sources:
                    sources.append(argv[i])
        elif path is None and not arg.startswith("--"):
            path = arg
        else:
            die(f"Unexpected argument: {arg}\n{USAGE}")
        i += 1
    if path is None:
        die(USAGE)
    return path, sources


def load_result(path):
    try:
        with open(path, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as error:
        die(f"Could not read/parse publish result JSON at {path}: {error}")
    if not isinstance(result, dict):
        die("Publish result must be a JSON object")
    return result


def quoted(text):
    escaped = str(text).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def grantee_label(rule):
    for kind in ("group", "user"):
        grantee = rule.get(kind)
        if grantee is not None:
            name = grantee.get("name") if isinstance(grantee, dict) else None
            return (
                f"{name} ({kind})"
                if isinstance(name, str) and name
                else f"Unnamed {kind}"
            )
    return "Unnamed rule"


def missing_capabilities(rule):
    if not isinstance(rule, dict):
        die("Each permissions entry must be an object")
    container = rule.get("capabilities") or {}
    capabilities = (
        (container.get("capability") or []) if isinstance(container, dict) else None
    )
    if not isinstance(capabilities, list):
        die("permissions[].capabilities.capability must be an array")
    modes = {}
    for capability in capabilities:
        if isinstance(capability, dict):
            modes.setdefault(capability.get("name"), set()).add(capability.get("mode"))
    # Absent, Deny, Allow+Deny, Unspecified, or anything else all count as missing.
    return [
        label for name, label in REQUIRED_CAPABILITIES if modes.get(name) != {"Allow"}
    ]


def main(argv=None):
    # argv: the arguments as a list, for callers that import this script; default: the command line.
    path, sources = parse_args(sys.argv[1:] if argv is None else list(argv))
    result = load_result(path)

    status = result.get("status")
    if status != "published":
        die(
            f'status is {status!r}, not "published" — surface the result\'s errors/warnings verbatim'
        )

    url = result.get("url")
    if not isinstance(url, str):
        die("Published result has no url string")
    data = result.get("data")
    name = data.get("name") if isinstance(data, dict) else None
    # The server returns url '' when it cannot build one.
    lines = [
        " — ".join(
            part
            for part in (f"Published {quoted(name)}" if name else "Published", url)
            if part
        )
    ]

    warnings = result.get("warnings") or []
    if not isinstance(warnings, list):
        die("warnings must be an array")
    for warning in warnings:
        message = warning.get("message") if isinstance(warning, dict) else warning
        if not isinstance(message, str) or not message:
            message = warning if isinstance(warning, str) else json.dumps(warning)
        lines.append(f"Warning: {message}")

    permissions = result.get("permissions")
    if result.get("permissionsNote") is not None:
        lines.append(NOT_VERIFIED)
    elif permissions is not None:
        if not isinstance(permissions, list):
            die("permissions must be an array")
        if not permissions:
            lines.append(NO_RULES)
        else:
            bullets = []
            for rule in permissions:
                missing = missing_capabilities(rule)
                if missing:
                    bullets.append(f"- {grantee_label(rule)}: {', '.join(missing)}")
            if bullets:
                lines.append(MISSING_HEADER)
                lines.extend(bullets)
    else:
        print("\n".join(lines))
        return

    if sources:
        lines.extend(
            f"Viewers also need API Access on the published data source {quoted(s)}."
            for s in sources
        )
    elif sources is not None:
        lines.append("Viewers also need API Access on the published data source.")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
