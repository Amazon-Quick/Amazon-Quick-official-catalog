---
description: "README for selling-partner-finance-month-end-closer: overview, the required Amazon Selling Partner built-in connector prerequisite, installation, and getting started."
last_updated: "2026-11-13"
origin: original
---

# Selling Partner Finance Month-End Closer (`selling-partner-finance-month-end-closer`)

Closes and reconciles a seller's completed Amazon month through the Selling Partner API (SP-API) finances operations, read-only, and produces an accountant-ready summary.

## Overview
Retrieves the close for one completed month, shows how settlements and balances reconcile to the month's net proceeds, and helps the seller confirm which payouts reached the bank using deposit amounts and dates they paste in. It has no bank access, posts no entries, changes no records, and never files, pays, or moves money. Outputs are informational and are not accounting, tax, or financial advice.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in AWS Quick, which exposes the month-end closing operation this skill uses. The connector authenticates as the seller and provides the merchant account and marketplace for the session.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot retrieve a close.

## Installation
1. In AWS Quick on desktop, go to Customize > Skills, choose Browse all, select the Official tab, and search for the skill by name. Choose Install. See [Browsing for more skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html).
2. Connect and authenticate the Amazon Selling Partner connector. Under Customize > Connectors, find Amazon Selling Partner and choose Install.

## Getting started
Ask, for example, "help me close last month" or "have I received all my payouts for October?" The skill reconciles the month, lists payouts awaiting confirmation, and asks you to paste the deposits you see in your bank.
