#!/usr/bin/env python3
"""
description: Wire published datasources or files in the workspace's Data folder into a scaffolded data-app .twb.
last_updated: 2026-11-22

Wire one or more datasources (published, or files in the workspace's `Data/`)
into a scaffolded data-app `.twb`.

`scaffold-data-app` emits a workbook with TWO empty `<datasources />` anchors
(workbook root + worksheet `<view>`). Until both are filled the extension's
`getAllDataSourcesAsync()` finds nothing and renders "no data source found in
the workbook." This fills both with N datasources, keeping each
join key (`sqlproxy.<hash>` or `federated.<hash>`) byte-identical everywhere.

A script, not freehand XML, because the wiring spans coordinated locations that
must agree exactly (root datasource `name`, root `relation connection`, view
`datasource name`, and for the primary `datasource-dependencies datasource`);
miss one and the workbook silently reaches no data.

Every datasource is listed on the extension's host sheet `<view>`: the server
only connects and keeps datasources listed there, so one listed only elsewhere
fails at query time. The first datasource is the primary (it alone gets
`datasource-dependencies`); the app finds the rest by caption via
`getAllDataSourcesAsync()`.

Usage: python3 wire_datasource.py <path-to.twb> <descriptor.json>

descriptor.json (Claude assembles from list-datasources + get-datasource-metadata;
list ONLY the fields the app will query). Either one datasource:
  {
    "caption":      "Superstore Datasource",
    "repositoryId": "SuperstoreDatasource",   // published DS contentUrl (== repo-location id / dbname)
    "connectionName": "sqlproxy.<hash>",  // optional, generated if omitted
    "fields": [
      { "name": "Profit", "datatype": "real",   "role": "measure"   },
      { "name": "Region", "datatype": "string", "role": "dimension" }
    ]
  }
or an embedded file (the file must already be in the workspace):
  {
    "type":     "file",
    "caption":  "Sample - Superstore",
    "file":     "Data/Datasources/Sample - Superstore.xls",  // Excel or CSV
    "table":    "Orders",                                    // Excel only: the sheet
    "fields": [ ...as above... ]
  }
or any number of either, primary first, wired in a single run:
  { "datasources": [ { ...as above... }, { ...as above... } ] }
"""

import json
import os
import secrets
import string
import sys

import defusedxml.ElementTree as ET
from defusedxml import DefusedXmlException
from file_formats import FORMAT_BY_EXTENSION, bracket

# The exact empty anchor emitted by the scaffold template. Matched literally.
EMPTY_ANCHOR = "<datasources />"


def die(message):
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


# XML attribute-value escaping (single-quoted attrs + element text).
def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
    )


# datatype -> Tableau column `type`.
def type_of(datatype):
    d = str(datatype).lower()
    if d in ("real", "integer"):
        return "quantitative"
    if d in ("date", "datetime"):
        return "ordinal"
    return "nominal"


# Derive a field's attributes once, reused across the root metadata-record, view
# column, and column-instance so all three agree.
def derive_field(field, ordinal, error_prefix=""):
    name = field.get("name") if isinstance(field, dict) else None
    if not name or not isinstance(name, str):
        die(
            f'{error_prefix}Every field needs a string "name" (field #{ordinal} was {json.dumps(field, separators=(",", ":"))}).'
        )
    datatype = str(field.get("datatype") or "string").lower()
    role = "measure" if field.get("role") == "measure" else "dimension"
    is_measure = role == "measure"
    field_type = type_of(datatype)
    # Spatial fields aggregate with Collect (a geometry union), not Sum/Count.
    aggregation = (
        "Collect" if datatype == "spatial" else ("Sum" if is_measure else "Count")
    )
    return {
        "name": name,
        "datatype": datatype,
        "role": role,
        "type": field_type,
        "ordinal": ordinal,
        "aggregation": aggregation,
        # role attribute: 0 = dimension, 1 = measure
        "roleAttr": 1 if is_measure else 0,
        "localName": f"[{name}]",
        # column-instance derivation + name token: [sum:Profit:qk] / [none:Region:nk]
        "derivation": "Sum" if is_measure else "None",
        "instanceName": f"[sum:{name}:qk]" if is_measure else f"[none:{name}:nk]",
    }


def generate_connection_name(prefix):
    def token():
        alphabet = string.ascii_lowercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(11))

    return f"{prefix}.{token()}{token()}"


def parse_fields(descriptor, error_prefix):
    fields_in = (
        descriptor.get("fields") if isinstance(descriptor.get("fields"), list) else []
    )
    if len(fields_in) == 0:
        die(
            f'{error_prefix}Descriptor "fields" must list at least one field the app will query.'
        )
    return [derive_field(f, i, error_prefix) for i, f in enumerate(fields_in)]


# Validate one datasource descriptor. `error_prefix` names the datasource in errors when wiring several.
def parse_datasource(descriptor, error_prefix=""):
    if not isinstance(descriptor, dict):
        die(f"{error_prefix}Descriptor must be a JSON object.")
    kind = descriptor.get("type", "published")
    if kind == "file":
        return parse_file_datasource(descriptor, error_prefix)
    if kind != "published":
        die(
            f'{error_prefix}Descriptor "type" must be "published" or "file" (got {json.dumps(kind)}).'
        )
    for key in ("caption", "repositoryId"):
        value = descriptor.get(key)
        if not isinstance(value, str) or not value:
            die(f'{error_prefix}Descriptor is missing required string "{key}".')

    fields = parse_fields(descriptor, error_prefix)

    connection_name = descriptor.get("connectionName")
    if connection_name and not connection_name.startswith("sqlproxy."):
        die(
            f'{error_prefix}connectionName must start with "sqlproxy." (got "{connection_name}").'
        )

    return {
        "type": "published",
        "caption": descriptor["caption"],
        "repositoryId": descriptor["repositoryId"],
        "fields": fields,
        "connectionName": connection_name,
    }


def parse_file_datasource(descriptor, error_prefix):
    for key in ("caption", "file"):
        value = descriptor.get(key)
        if not isinstance(value, str) or not value:
            die(f'{error_prefix}Descriptor is missing required string "{key}".')
    file_path = descriptor["file"].replace("\\", "/")
    parts = file_path.split("/")
    if (
        len(parts) < 2
        or parts[0] != "Data"
        or any(part in ("", ".", "..") for part in parts)
    ):
        die(
            f'{error_prefix}"file" must be a path inside the workspace Data/ folder, '
            f'e.g. "Data/Datasources/Sales.xlsx" (got "{descriptor["file"]}").'
        )
    file_format = FORMAT_BY_EXTENSION.get(os.path.splitext(file_path)[1].lower())
    if not file_format:
        die(
            f'{error_prefix}"file" must end in {", ".join(FORMAT_BY_EXTENSION)} (got "{file_path}").'
        )
    try:
        source = file_format(file_path, descriptor.get("table"))
    except ValueError as error:
        die(f"{error_prefix}{error}")

    fields = parse_fields(descriptor, error_prefix)

    return {
        "type": "file",
        "caption": descriptor["caption"],
        "file": file_path,
        "source": source,
        "fields": fields,
        "connectionName": None,  # always generated
    }


def parse_descriptor(descriptor):
    if isinstance(descriptor, dict) and "datasources" in descriptor:
        extra_keys = [key for key in descriptor if key != "datasources"]
        if extra_keys:
            die(
                f'Descriptor mixes "datasources" with top-level {", ".join(json.dumps(k) for k in extra_keys)}. '
                "Put every datasource's settings inside its datasources[] entry."
            )
        entries = descriptor["datasources"]
        if not isinstance(entries, list) or len(entries) == 0:
            die('Descriptor "datasources" must list at least one datasource.')
        datasources = [
            parse_datasource(d, f"datasources[{i}]: ") for i, d in enumerate(entries)
        ]
    else:
        datasources = [parse_datasource(descriptor)]

    seen_repository_ids = set()
    for i, ds in enumerate(datasources):
        if ds["type"] != "published":
            continue
        if ds["repositoryId"] in seen_repository_ids:
            die(
                f'datasources[{i}]: repositoryId "{ds["repositoryId"]}" is listed more than once.'
            )
        seen_repository_ids.add(ds["repositoryId"])

    # app.js finds each datasource by caption, so captions must be distinct.
    caption_owner = {}
    for i, ds in enumerate(datasources):
        if ds["caption"] in caption_owner:
            die(
                f'datasources[{i}]: caption "{ds["caption"]}" is already used by datasources[{caption_owner[ds["caption"]]}]. '
                'Give each datasource a distinct caption (e.g. "Sales Orders" / "Finance Orders") so app.js can find it by name.'
            )
        caption_owner[ds["caption"]] = i

    # Single source of truth for each join key; they must be distinct across datasources.
    explicit_names = [
        ds["connectionName"] for ds in datasources if ds["connectionName"]
    ]
    if len(set(explicit_names)) != len(explicit_names):
        die("connectionName values must be unique across datasources.")
    used = set(explicit_names)
    for ds in datasources:
        if not ds["connectionName"]:
            prefix = "sqlproxy" if ds["type"] == "published" else "federated"
            name = generate_connection_name(prefix)
            while name in used:
                name = generate_connection_name(prefix)
            ds["connectionName"] = name
            used.add(name)
        if ds["type"] == "published":
            ds["relationConnection"] = ds["connectionName"]
        else:
            ds["relationConnection"] = (
                f"{ds['source'].connection_class}.{ds['connectionName'].split('.', 1)[1]}"
            )
    return datasources


def root_datasource_xml(ds):
    return (
        published_datasource_xml(ds)
        if ds["type"] == "published"
        else file_datasource_xml(ds)
    )


def file_connection_xml(source):
    attrs = " ".join(
        f"{name}='{esc(value)}'" for name, value in source.connection_attrs().items()
    )
    return f"<connection class='{source.connection_class}' {attrs} />"


def file_datasource_xml(ds):
    metadata_records = "\n".join(
        f"""          <metadata-record class='column'>
            <remote-name>{esc(f["name"])}</remote-name>
            <remote-type>{5 if f["type"] == "quantitative" else 129}</remote-type>
            <local-name>{esc(f["localName"])}</local-name>
            <parent-name>{esc(bracket(ds["source"].relation_name))}</parent-name>
            <remote-alias>{esc(f["name"])}</remote-alias>
            <ordinal>{f["ordinal"]}</ordinal>
            <local-type>{esc(f["datatype"])}</local-type>
            <aggregation>{f["aggregation"]}</aggregation>
            <contains-null>true</contains-null>
          </metadata-record>"""
        for f in ds["fields"]
    )
    return f"""    <datasource caption='{esc(ds["caption"])}' inline='true' name='{esc(ds["connectionName"])}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{esc(ds["caption"])}' name='{esc(ds["relationConnection"])}'>
            {file_connection_xml(ds["source"])}
          </named-connection>
        </named-connections>
        <relation connection='{esc(ds["relationConnection"])}' name='{esc(ds["source"].relation_name)}' table='{esc(ds["source"].relation_table)}' type='table' />
        <metadata-records>
{metadata_records}
        </metadata-records>
      </connection>
    </datasource>"""


def published_datasource_xml(ds):
    metadata_records = "\n".join(
        f"""          <metadata-record class='column'>
            <remote-name>{esc(f["name"])}</remote-name>
            <remote-type>{5 if f["type"] == "quantitative" else 129}</remote-type>
            <local-name>{esc(f["localName"])}</local-name>
            <parent-name>[sqlproxy]</parent-name>
            <remote-alias>{esc(f["name"])}</remote-alias>
            <ordinal>{f["ordinal"]}</ordinal>
            <layered>true</layered>
            <local-type>{esc(f["datatype"])}</local-type>
            <aggregation>{f["aggregation"]}</aggregation>
            <contains-null>true</contains-null>
            <attributes>
              <attribute datatype='integer' name='field-type'>1</attribute>
              <attribute datatype='integer' name='role'>{f["roleAttr"]}</attribute>
            </attributes>
          </metadata-record>"""
        for f in ds["fields"]
    )
    return f"""    <datasource caption='{esc(ds["caption"])}' inline='true' name='{esc(ds["connectionName"])}' version='18.1'>
      <repository-location id='{esc(ds["repositoryId"])}' path='/datasources' revision='1.0' />
      <connection channel='https' class='sqlproxy' dbname='{esc(ds["repositoryId"])}' directory='dataserver' server-ds-friendly-name='{esc(ds["caption"])}' username=''>
        <relation type='collection'>
          <relation connection='{esc(ds["connectionName"])}' name='sqlproxy' table='[sqlproxy]' type='table' />
        </relation>
        <metadata-records>
{metadata_records}
        </metadata-records>
      </connection>
    </datasource>"""


def view_dependencies_xml(ds):
    view_columns = "\n".join(
        f"            <column aggregation='{f['aggregation']}' datatype='{esc(f['datatype'])}' name='{esc(f['localName'])}' role='{f['role']}' type='{f['type']}' />"
        for f in ds["fields"]
    )
    view_column_instances = "\n".join(
        f"            <column-instance column='{esc(f['localName'])}' derivation='{f['derivation']}' name='{esc(f['instanceName'])}' pivot='key' type='{f['type']}' />"
        for f in ds["fields"]
    )
    return f"""          <datasource-dependencies datasource='{esc(ds["connectionName"])}'>
{view_columns}
{view_column_instances}
          </datasource-dependencies>"""


# Check each join key sits where the server reads it, not just that it appears often enough.
def verify_wiring(wired, datasources):
    try:
        root = ET.fromstring(wired)
    except (ET.ParseError, DefusedXmlException) as error:
        die(f"Wired .twb is not valid XML ({error}) — refusing to write it.")
    primary_name = datasources[0]["connectionName"]

    root_datasources = {
        d.get("name"): d for d in root.findall("./datasources/datasource")
    }
    for ds in datasources:
        name = ds["connectionName"]
        root_ds = root_datasources.get(name)
        if root_ds is None:
            die(f"Root <datasources> is missing {name} — wiring incomplete.")
        relation_connection = ds["relationConnection"]
        if not any(
            r.get("connection") == relation_connection for r in root_ds.iter("relation")
        ):
            target = "itself" if relation_connection == name else relation_connection
            die(
                f"Root datasource {name} has no relation connection to {target}, so wiring is incomplete."
            )
        if ds["type"] == "file" and not any(
            c.get("name") == relation_connection
            for c in root_ds.iter("named-connection")
        ):
            die(
                f"Root datasource {name} has no named connection {relation_connection}, so wiring is incomplete."
            )

    # The server only connects datasources listed on the host sheet's view.
    host_view = next(
        (
            v
            for v in root.iter("view")
            if any(
                d.get("name") == primary_name
                for d in v.findall("./datasources/datasource")
            )
        ),
        None,
    )
    if host_view is None:
        die(
            f"No worksheet view lists the primary datasource {primary_name} — wiring incomplete."
        )
    listed = {d.get("name") for d in host_view.findall("./datasources/datasource")}
    missing = [
        ds["connectionName"] for ds in datasources if ds["connectionName"] not in listed
    ]
    if missing:
        die(
            f"Host sheet view does not list {', '.join(missing)} — the server would not connect them."
        )
    if (
        host_view.find(f"./datasource-dependencies[@datasource='{primary_name}']")
        is None
    ):
        die(
            f"Host sheet view has no datasource-dependencies for the primary {primary_name} — wiring incomplete."
        )


def main(argv=None):
    # argv: the arguments as a list, for callers that import this script; default: the command line.
    argv = sys.argv if argv is None else ["wire_datasource.py", *argv]
    if len(argv) < 3:
        die("Usage: python3 wire_datasource.py <path-to.twb> <descriptor.json>")
    twb_path_arg, descriptor_path_arg = argv[1], argv[2]
    twb_path = os.path.abspath(twb_path_arg)

    try:
        with open(descriptor_path_arg, encoding="utf-8") as f:
            descriptor = json.load(f)
    except Exception as error:
        die(f"Could not read/parse descriptor JSON at {descriptor_path_arg}: {error}")
        return

    datasources = parse_descriptor(descriptor)
    primary = datasources[0]

    workspace = os.path.dirname(twb_path)
    for ds in datasources:
        if ds["type"] == "file" and not os.path.isfile(
            os.path.join(workspace, ds["file"])
        ):
            die(
                f"Datasource '{ds['caption']}' file \"{ds['file']}\" is not in the workspace ({workspace}). "
                "Copy it there first, at that path relative to the .twb."
            )

    # --- build the XML blocks ----------------------------------------------

    root_datasources = (
        "<datasources>\n"
        + "\n".join(root_datasource_xml(ds) for ds in datasources)
        + "\n  </datasources>"
    )

    view_entries = "\n".join(
        f"            <datasource caption='{esc(ds['caption'])}' name='{esc(ds['connectionName'])}' />"
        for ds in datasources
    )
    view_datasources = f"""<datasources>
{view_entries}
          </datasources>
{view_dependencies_xml(primary)}"""

    # --- apply, splitting on <worksheets> so each anchor is unambiguous ------

    try:
        with open(twb_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as error:
        die(f"Could not read .twb at {twb_path}: {error}")
        return

    split_idx = content.find("<worksheets>")
    if split_idx == -1:
        die("No <worksheets> element found — is this a scaffolded data-app .twb?")
    head = content[:split_idx]
    tail = content[split_idx:]

    if "class='sqlproxy'" in head or "class='federated'" in head:
        die(
            "This .twb is already wired. To change its datasources, re-scaffold, copy content/src/app.js "
            "into the new workspace, and wire every datasource in one run."
        )

    # Root anchor lives in the head (before <worksheets>).
    if EMPTY_ANCHOR not in head:
        die(
            f'Root "{EMPTY_ANCHOR}" anchor not found before <worksheets> — template drifted.'
        )
    head = head.replace(EMPTY_ANCHOR, root_datasources, 1)

    # View anchor is the first empty <datasources /> inside the worksheets section.
    if EMPTY_ANCHOR not in tail:
        die(
            f'View "{EMPTY_ANCHOR}" anchor not found inside <worksheets> — template drifted.'
        )
    tail = tail.replace(EMPTY_ANCHOR, view_datasources, 1)

    wired = head + tail

    # --- verify before writing ----------------------------------------------

    if EMPTY_ANCHOR in wired:
        die(
            "An empty <datasources /> anchor survived wiring — refusing to write a half-wired workbook."
        )
    verify_wiring(wired, datasources)

    with open(twb_path, "w", encoding="utf-8") as f:
        f.write(wired)
    for ds in datasources:
        print(
            f"✓ Wired datasource '{ds['caption']}' ({ds['connectionName']}) with {len(ds['fields'])} field(s) into {twb_path}",
            file=sys.stderr,
        )
    print(twb_path)


if __name__ == "__main__":
    main()
