---
description: "README for selling-partner-invite-secondary-users: overview, the required Amazon Selling Partner built-in connector prerequisite, installation, and getting started."
last_updated: "2026-09-15"
origin: original
---

# Selling Partner Invite Secondary Users (`selling-partner-invite-secondary-users`)

Helps the primary user (account owner or administrator) of a Selling Partner API (SP-API) Seller Central account invite their team onto the Selling Partner plugin, advisory and read-only.

## Overview
Confirms the person is the account administrator, then guides them through granting each secondary user AI-agent access on the Manage Agents page in Seller Central. When running in Amazon Quick, it adds a second grant: inviting the user as a collaborator on the Quick account. It performs no write action; every grant is a UI step the human takes.

## Pre-requisites
- Type: built-in cloud connector
- Which: the "Amazon Selling Partner" connector in Amazon Quick. This skill assumes the plugin is already connected and authenticated; it does not itself change access. The connector authenticates as the seller.
- Runtime: cloud
- Required or optional: required. Without the plugin connected, there is nothing to grant secondary users access to, so the skill points the primary user to the connect flow first.

The connector is offered during Amazon Quick onboarding. If the primary user connected and authenticated it, this skill is available. If they skipped connector setup and later added this skill manually, they must connect and authenticate the "Amazon Selling Partner" connector before it can run.

## Installation
1. Connect and authenticate the "Amazon Selling Partner" connector when prompted during onboarding, or from Settings > Capabilities.
2. If you added this skill manually from the catalog, add it in Customize > Skills, then confirm the connector above is connected.

## Getting started
As the account administrator, ask to invite a teammate, for example "let my ops manager use the plugin", and the skill will confirm your role, walk you through the Manage Agents grant in Seller Central, and (in Amazon Quick) the collaborator invite, then recap what the secondary user must still do themselves.
