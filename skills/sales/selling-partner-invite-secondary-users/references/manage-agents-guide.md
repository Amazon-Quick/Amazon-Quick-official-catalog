---
description: "The exact Manage Agents grant steps in Seller Central for giving a secondary user AI-agent access: who can do it, the steps, what the grant does and does not do, and good practice."
last_updated: "2026-09-15"
origin: original
---

# Manage Agents: granting AI-agent access to a secondary user

Granting a secondary user access to the Selling Partner plugin is done in Seller Central, on the Manage Agents page. There is no operation for this; it is a UI action taken by the account owner or an administrator.

## Who can do this
- Only the account owner or an administrator of the Seller Central account.
- A secondary (non-admin) user cannot grant themselves access; they must ask an administrator.

## Steps (account owner / administrator)
1. Sign in to Seller Central with the owner/administrator account.
2. Go to the Manage Agents page.
3. Find the user you want to update.
4. Enable that user's AI agent access. (To revoke later, come back here and disable it.)

## What this grant does, and does not do
- Does: allow that secondary user to authorize the Selling Partner plugin in their AI assistant, scoped to their Seller Central roles.
- Does not: connect the plugin for them. After you enable access, the secondary user must still, on their own side:
  1. Install or open the plugin in their assistant,
  2. Sign in with their own Amazon selling account, and
  3. Authorize access when prompted.
- Write actions the agent takes still require approval by default, per the plugin's human-in-the-loop model.

## Good practice
- Grant access only to trusted users; AI-agent access lets that user act on the account through the plugin.
- Changes can take a few minutes to apply.
- Keep a record of who you granted access to, and disable access on Manage Agents when someone no longer needs it.

Source: Seller Central Help, "Selling Partner plugin, managing access for secondary users."
