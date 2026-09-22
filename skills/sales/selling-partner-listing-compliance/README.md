---
description: "README for selling-partner-listing-compliance: overview, the required Amazon Selling Partner built-in connector prerequisite (including the Seller Assistant tools it must expose), how sibling listing skills call this gate, and getting started."
last_updated: 2026-09-16
origin: original
---

# SP-API Listing Compliance Guardrails (`selling-partner-listing-compliance`)

A pre-flight compliance gate that runs before any Selling Partner API (SP-API) listing write, so the agent knows which Amazon listing requirements and regulatory rules apply and gets the seller's input where only the seller can answer.

## Overview
Classifies the product against a regulatory map (FDA, EPA, CPSC, FCC, FTC, required disclosures, GTIN, category gating), asks the seller once for the compliance facts only they know, confirms the current rules through Amazon's Seller Assistant, checks account-side gating on the ASIN, and presents a met / unmet / not-applicable checklist for an explicit go or no-go. It never writes a listing itself; the write stays in the sibling skill that owns it, behind that skill's own preview-and-approval gate. It is the compliance member of the SP-API listing troubleshooter family, alongside `selling-partner-listing-issues`, `selling-partner-listing-buyability`, `selling-partner-listing-searchability`, and the `selling-partner-listing-troubleshooter` router.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick. This skill needs three of its operations: the Seller Assistant create and get tools (`sellerAssistant_sellerAssistantCreate`, `sellerAssistant_sellerAssistantGet`) for confirming current rules, and the listings restrictions operation (`listings_getListingsRestrictions`) for the account-side gating check. The connector authenticates as the seller.
- Runtime: cloud
- Required or optional: required. Without Seller Assistant the gate can still run on the reference map alone, but the skill must say the live check was unavailable.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

Establishing the active seller account and marketplace is handled by the session's account context (the connected Amazon Selling Partner connector); this skill reuses it.

## How sibling skills use this gate
The issue fixer, buyability, and searchability skills each carry a rule that a change must comply with Amazon's policies and that a non-compliant change is flagged and pointed to the policy. This skill is where they point. A sibling calls this gate before its preview step whenever the proposed change touches product claims, ingredients, category, condition, images, or identifiers (for example a title that adds "FDA approved", a bullet that adds an antimicrobial claim, a new main image for a children's product, a condition change, or a new GTIN). Plain price, quantity, or typo fixes do not need the gate. On a go, control returns to the sibling and its own preview-approve-verify triad runs.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected and that its tool search returns the Seller Assistant tools.

## Getting started
Ask "can I list this?" or "what do I need to sell a children's night light?", and the skill will classify the product, ask you once for the facts it cannot know, confirm the current rules with Seller Assistant, check whether you are gated, and show you a checklist before anything is written.
