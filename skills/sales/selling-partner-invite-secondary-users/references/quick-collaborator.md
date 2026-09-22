---
description: "The Amazon Quick-only second grant: inviting a secondary user as a collaborator on your Quick account, why both grants are required on Quick, and the steps."
last_updated: "2026-09-15"
origin: original
---

# Quick only: invite the user as a collaborator on your Quick account

This applies only when the plugin is used in Amazon Quick. In a non-Quick assistant there is no collaborator step; skip it.

## Why there are two grants on Quick
For a secondary user to use the Selling Partner plugin inside Quick, they need both:
1. Seller Central, Manage Agents: AI-agent access enabled (see manage-agents-guide.md). This is the Amazon-side authorization.
2. Quick, collaborator: access to your Quick account, because the plugin and its skills are installed and used within a Quick account. The Manage Agents grant does not by itself give the user access to your Quick workspace.

If you grant only Manage Agents access but never add the user to Quick, they cannot use the plugin in Quick. If you add them to Quick but skip Manage Agents, they cannot authorize the plugin against your Seller Central account. Both are required on Quick.

## Steps (Quick account owner)
1. Open Amazon Quick.
2. Invite the secondary user as a collaborator on your Quick account (use the same person or email you granted on Manage Agents).
3. Have the user accept the collaborator invite, then sign in to the plugin with their own Amazon selling account to authorize access.

## Note
- Quick subscription and Selling Partner plugin access activate on their own schedules; the user needs plugin access active on their account too.
- Exact Quick menu labels can vary as Quick evolves; the requirement is that the user must be a collaborator on your Quick account in addition to the Manage Agents grant.
