---
name: catalog-poc-test-skill
display_name: Catalog POC Test Skill
description: "Test-only skill for the salesforce-catalog-poc branch. Use when the user asks to run the catalog POC test skill. It replies with one fixed sentence so a tester can confirm the alternate catalog branch was loaded."
created_date: "2026-11-03"
last_updated: "2026-11-03"
license: "MIT-0"
checksum: "sha256:f67b4b1a5898377053bae9f8d8cb8c18ea8da6938e558dbbac3f7307b412109e"
---

# Catalog POC Test Skill

This skill exists only to test that Amazon Quick reads the official catalog from the
`salesforce-catalog-poc` branch. It does not read or change any data.

When the user asks to run it, reply with exactly this sentence and nothing else:

Catalog POC test skill is working.
