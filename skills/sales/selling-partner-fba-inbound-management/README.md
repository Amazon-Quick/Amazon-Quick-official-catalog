---
description: "README for selling-partner-fba-inbound-management: overview, the required Amazon Selling Partner built-in connector prerequisite, installation, and getting started."
last_updated: "2026-09-15"
origin: original
---

# Selling Partner FBA Inbound Management (`selling-partner-fba-inbound-management`)

Guides a Fulfillment by Amazon (FBA) seller through the Selling Partner API (SP-API) inbound pipeline: create an inbound plan, set packing, choose placement, book transportation, confirm a delivery window, and confirm the shipment, plus status checks, tracking, labels, prep, and modify or cancel.

## Overview
Runs the sequential inbound pipeline (create, pack, place, transport, deliver, ship) end to end, polling each asynchronous operation to a confirmed result before advancing and pausing at every decision gate. Diagnosis and status reads are safe; the two money-charging actions (confirming a placement option and confirming transportation) are permanent and sit behind an explicit, restated, typed confirmation. It is the shipment-execution member of the SP-API seller family, alongside selling-partner-stockout-prevention (which routes a seller here to create or expedite a shipment).

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick, which exposes the Fulfillment Inbound operations this skill uses (create inbound plan, set packing, generate/list/confirm packing, placement, transportation, and delivery windows, operation status, shipment reads, tracking updates, labels, prep, India compliance and self-ship appointments, and cancel). The connector authenticates as the seller and resolves the merchant account and marketplace(s) at the start of the session.
- Runtime: cloud
- Required or optional: required. Without it connected, the skill cannot create or manage inbound shipments.

The connector is offered during Amazon Quick onboarding. If the seller connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
Ask to send inventory to Amazon, for example "create an inbound plan to ship 100 units to FBA" or "what inbound plans do I have going?", and the skill will drive the pipeline stage by stage, show every fee before you commit, and never confirm a fee-charging step without your explicit typed confirmation.
