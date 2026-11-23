---
description: "Technical and business asset families in the Informatica catalog, their trust signals, and how to search for each asset type."
last_updated: 2026-11-13
origin: original
---
# Asset Types — Full Reference

> Canonical source for SKILL.md §3 (Asset Types). Read when the intent targets a specific asset type, or the agent needs to decide how to search for a type.

The catalog holds two families of assets. Every strategy first classifies its target into one of these families before deciding which segments to pull and which trust signal applies.

## Supertypes vs. specific classTypes

Technical assets are organized as a **type hierarchy**: supertypes (`core.Dataset`, `core.DataElement`) generalize many specific `classType`s. The table below shows the supertype and one common concrete `classType` as an example — real catalogs contain many more subtypes per supertype (Oracle Table, Snowflake View, S3 File, etc.), all rolled up under the same supertype. The high level abstract type for all technical assets is `core.IClassTechnical`.

- **`Dataset`** — any tabular / file-shaped container. Examples: `com.infa.odin.models.relational.Table`, `com.infa.odin.models.file.File`, plus views, external tables, and other source-specific subtypes.
- **`DataElement`** — any field / column-shaped member of a Dataset. Example: `com.infa.odin.models.relational.Column`, plus file fields and other subtypes.

Business assets share a common abstract type called `core.IClassBusiness`. More specific common abstract types are `com.infa.ccgf.models.governance.GlossaryBase` which covers (`com.infa.ccgf.models.governance.BusinessTerm`, `com.infa.ccgf.models.governance.Domain`, `com.infa.ccgf.models.governance.SubDomain`, `com.infa.ccgf.models.governance.Metric`, `com.infa.ccgf.models.governance.Policy`, `com.infa.ccgf.models.governance.System`).

## Asset table

| Asset Type | Supertype | Example `classType` | Family | Key segments |
|-----------|-----------|---------------------|--------|--------------|
| Table | `core.Dataset` | `com.infa.odin.models.relational.Table` | Technical | summary, hierarchy, selfAttributes, dataClassification, stakeholdership |
| File | `core.Dataset` | `com.infa.odin.models.file.File` | Technical | summary, dataClassification, stakeholdership |
| Column | `core.DataElement` | `com.infa.odin.models.relational.Column` | Technical | summary, glossary, dataClassification, selfAttributes |
| Business Term | — | `com.infa.ccgf.models.governance.BusinessTerm` | Business | summary, stakeholdership, neighborhood |
| Metric | — | `com.infa.ccgf.models.governance.Metric` | Business | summary, stakeholdership |
| Domain | — | `com.infa.ccgf.models.governance.Domain` | Business | summary, stakeholdership |
| SubDomain | — | `com.infa.ccgf.models.governance.SubDomain` | Business | summary, stakeholdership |
| Policy | — | `com.infa.ccgf.models.governance.Policy` | Business | summary, selfAttributes, stakeholdership |
| System | — | `com.infa.ccgf.models.governance.System` | Business | summary, stakeholdership |

`classType` values above are examples of what a real search returns; do **not** hard-code them as the only accepted match. When the intent is "any table" or "any column" regardless of source, use NL mode (§3.4 A in this file) — the `filterSpec.types` path is unavailable (see §3.4 B).

## Family rules

- **Technical assets** use `certified: true` as the primary trust signal (Dataset-only, per §1 principle 3 in SKILL.md).
- **Business assets** use `assetLifecycle` (`Published` as a trust signal above `Draft` and `Obsolete`) as the trust signal. They are not "certified" in the catalog sense.
- `stakeholdership` applies to both families.
- `hierarchy` is meaningful for containers along the technical chain: `core.Resource → core.DataSource (Database/Schema) → core.Dataset → core.DataElement`. Also applies to `Domain → SubDomain → BusinessTerm` on the business side.
- Glossary parenting is asymmetric, not free-form. Domain is a root — it has no parent. SubDomain can be parented under a Domain or another SubDomain. Metric can be parented under a Domain or SubDomain. BusinessTerm is the flexible one — it can be parented under any of Domain, SubDomain, BusinessTerm, or Metric. Because a hierarchy walk over glossary assets is therefore not a strict Domain → SubDomain → Term chain, always read classType on the parent before drawing a governance conclusion — do not infer it from position in the tree.
- `dataClassification` (PII / sensitivity labels) / `glossary` (Business Meaning of technical assets) applies primarily to technical assets. Business/Manual Data Elements are exceptions.

## §3.4 How to search by type

Two ways to constrain a search to a type — pick based on whether the intent is supertype-level ("any table") or subtype-specific ("only Snowflake tables"):

**A. NL mode — say the type in plain English.** The NL parser resolves common type words to the right supertype/classType internally. This is the **only** path for supertype-level intent ("any Dataset", "any DataElement") — see §3.4 B for why the structured supertype path is unavailable.

- `"Oracle Tables"` → any Dataset on Oracle sources
- `"show columns from table customers"` → DataElements under a specific parent
- `"my business terms"` → BusinessTerm owned by the caller
- `"find files with customer data"` → File Datasets
- `"show domains linked to policy GDPR"` → Domain related to a Policy

**B. KEYWORD mode — pass fully-qualified names via `filterSpec.classType` (multivalued, `in` operator).** Use this when the caller has named specific subtypes and you can enumerate them.

```
filterSpec: { classType: ["com.infa.odin.models.relational.Table"] }
filterSpec: { classType: ["com.infa.ccgf.models.governance.BusinessTerm",
                          "com.infa.ccgf.models.governance.Metric"] }
```

**Do not use `filterSpec.types`.** Although the tool schema lists `types` as a filter field, the server discards any caller-supplied value — the supertype policy is enforced server-side and cannot be widened or narrowed by the client. Passing `types` is a silent no-op. For supertype-level intent, use NL mode (§3.4 A) instead.

Use `filterSpec.resourceType` (e.g. `Oracle`, `Snowflake`, `MySql`, `Postgres`, `Redshift`) to narrow technical assets by catalog **source**. Combine `classType` + `resourceType` for "Snowflake tables only":

```
filterSpec: {
  classType: ["com.infa.odin.models.relational.Table"],
  resourceType: ["Snowflake"]
}
```

## Business-asset key fields (Metric, BusinessTerm, glossary parenting)

The asset table's segment column names the *catalog fetch* — but a business asset's real payload lives in specific fields that a generic report will miss. Surface these when the answer depends on them:

- **`Metric` — `business logic` field.** The tenant's actual calculation formula (status filters, currency conversion, window, join path) lives here — the business-side analogue of a view's `sourceStatementText`. When reporting a Metric, quote the `business logic` formula, not just the prose description; that's what the user has to reproduce if they query the source tables directly.
- **`BusinessTerm` — `alias names` field.** Synonyms the concept can appear under in tables. If the term is "Net Revenue" but tables use `NET_SALES_AMT`, the alias tells you so. Treat aliases as extra search probes; surface them explicitly when you report the concept → data mapping.
- **Glossary parenting is not a strict chain.** Parenting follows the asymmetric rules above (Domain is a root; BusinessTerm is the most flexible), so a `hierarchy` walk over glossary assets is NOT a strict `Domain → SubDomain → Term` chain. Do NOT assume the parent's class; read `classType` on the parent before drawing a governance conclusion.

## Additional catalog categories

Present in `search_assets` but not modelled as first-class targets by this skill — treat as opaque matches and drill in with `get_asset_details` if a query surfaces them: Process, Project, AI (`AIModel`, `AISystem`), Business Area, Legal Entity, Geography, Regulation. If a user question is clearly aimed at one of these, state the limitation before proceeding.
