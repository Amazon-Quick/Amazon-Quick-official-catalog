---
description: "README for selling-partner-seller-analytics: overview, the required Amazon Selling Partner built-in connector prerequisite, installation, and getting started."
last_updated: "2026-09-15"
origin: original
---

# Selling Partner Seller Analytics (`selling-partner-seller-analytics`)

Answers a Fulfillment by Amazon (FBA) seller's business-performance questions (inventory health, traffic, and sales) through the Selling Partner API (SP-API) analytics operations, read-only, in plain language.

## Overview
Discovers the right metric from live metadata (never guesses), queries it with a correctly-shaped request (a required date granularity and a required marketplace filter), and explains the result tied to the seller's question. It never changes a price, listing, or shipment. It is the reporting member of the SP-API seller family; when a stockout risk surfaces that the seller wants to act on, it points them to selling-partner-stockout-prevention.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the analytics operations this skill uses (metric metadata discovery and metric data retrieval). The connector authenticates as the seller and resolves the merchant account and marketplace(s) at the start of the session.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot discover or query analytics.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Ask a business-performance question, for example "am I at risk of any stockouts?" or "how are my sessions this month by ASIN?", and the skill will discover the right metric, query it for a stated date window, and explain the numbers in plain language, read-only.
