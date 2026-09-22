---
description: "README for selling-partner-listing-buyability: overview, the required Amazon Selling Partner built-in connector prerequisite, and getting started."
last_updated: 2026-09-15
origin: original
---

# SP-API Listing Buyability Troubleshooter (`selling-partner-listing-buyability`)

Diagnoses why a Selling Partner API (SP-API) listing is not buyable and either fixes the offer with the seller's approval or routes the cause to the right skill.

## Overview
Checks the three conditions that make a listing buyable (a complete product, a valid purchasable offer, and available inventory), identifies which one is missing, and relays the reason plus the next step. It fixes the offer through a previewed, approved patch; product-completeness and inventory causes are routed to sibling skills. It is the buyability member of the SP-API listing troubleshooter family, alongside `selling-partner-listing-issues`, `selling-partner-listing-searchability`, and the `selling-partner-listing-troubleshooter` router.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the listings operations this skill uses (searching a seller's listing items, and patching a listing item). The connector authenticates as the seller.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot read listings or fix the offer.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

Establishing the active seller account and marketplace is handled by the session's account context (the connected Amazon Selling Partner connector); this skill reuses it.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Ask why a product is not selling, for example "why can't customers buy this?" or "why is SKU 12345 inactive?", and the skill will inspect the listing, identify the cause, and preview an offer fix or route you to the right next step.
