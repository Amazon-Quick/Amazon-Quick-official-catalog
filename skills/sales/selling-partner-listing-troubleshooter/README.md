---
description: "README for selling-partner-listing-troubleshooter: overview, the required Amazon Selling Partner built-in connector prerequisite, and getting started."
last_updated: 2026-09-15
origin: original
---

# SP-API Listing Troubleshooter (`selling-partner-listing-troubleshooter`)

The front door for any "something's wrong with my listing" question in the Selling Partner API (SP-API): reads the symptom and routes the seller to the right specialist skill.

## Overview
Does one quick read of a listing's status and issues, identifies the symptom, and routes the seller to the specialist that fits: `selling-partner-listing-issues`, `selling-partner-listing-buyability`, or `selling-partner-listing-searchability`. It diagnoses and directs only; it makes no changes itself. It is the router of the SP-API listing troubleshooter family.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the listings search operation this skill uses to read a listing's status and issues. The connector authenticates as the seller.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot read the listing to classify the symptom.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

Establishing the active seller account and marketplace is handled by the session's account context (the connected Amazon Selling Partner connector); this skill reuses it.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Say something like "something's wrong with my listing" or "troubleshoot SKU 12345", and the skill will read the symptom and send you to the right specialist with a reason.
