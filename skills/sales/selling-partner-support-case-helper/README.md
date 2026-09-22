---
description: "README for selling-partner-support-case-helper: overview, the required Amazon Selling Partner connector prerequisite, and getting started."
last_updated: 2026-09-18
origin: original
---

# SP-API Support Case Helper (`selling-partner-support-case-helper`)

Guides an Amazon seller (Seller Central) to the right Amazon support path and prepares a clean, PII-free case summary they can paste into Seller Central. Advisory by default; it never submits a case without the seller's explicit confirmation.

## Overview
Gathers a few case details, resolves the Marketplace ID (seller input > session context > ask; never fabricated), and writes a short human-voice summary. If the Amazon Selling Partner connector later exposes a tool that can contact Seller Support or create a case, the skill uses it only after explicit seller confirmation; otherwise it points the seller to the Seller Central Help Center. Redacts PII and scopes the summary to the Amazon Selling Partner connector only. Not for Vendors (Vendor Central) or non-Seller Central use cases.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick. This skill calls no SP-API tools by default; the connector provides the account/session context (Marketplace ID) it reuses. If or when the connector exposes a Seller Support / case-creation tool, the skill can use it after explicit seller confirmation.
- Required or optional: optional for the advisory (summary + Help Center link) path; the connector's session context improves identifier fill.

Establishing the active seller account and marketplace is handled by the session's account context (the connected Amazon Selling Partner connector); this skill reuses it.

## Getting started
Ask "I need to contact Amazon about my account" or "can you connect me with Amazon support?", and the skill will gather the details, write a PII-free summary, and point you to the Seller Central Help Center to open the case.
