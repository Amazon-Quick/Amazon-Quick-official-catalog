---
description: "Microsoft OneDrive knowledge base: console-only in this skill, with the prerequisite checklist for admin-managed setup and the values the admin enters in the console. Read it when setting up a OneDrive knowledge base."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/onedrive-knowledge-base.html
---

# Microsoft OneDrive knowledge base

| Field | Value |
|---|---|
| Skill connector key | `onedrive` (the same key as the OneDrive action connector in [onedrive-action.md](onedrive-action.md)) |
| Suite | Microsoft 365 |
| Capability | Knowledge base |
| Admin-managed setup | Console-only in this skill. Never call `enable_kb_integration` for `onedrive` (Rule 7 in SKILL.md). |
| User-managed setup | Console-only. |
| Secret | None. The admin enters the service credentials directly in the console; never create a Secrets Manager secret for them and never grant the server access to one. |

For the current setup methods, prerequisites, and console steps, fetch the AWS Quick guide in this file's `source_url` and the pages it links. When you walk the admin through the console flow, name and link that guide, https://docs.aws.amazon.com/quick/latest/userguide/onedrive-knowledge-base.html, so they can follow its steps and screenshots.

## Choosing the setup method

Recommend the method for `{org_size}` per `<Definition - Org Size Recommendation>` in SKILL.md. User-managed setup indexes only the signing-in user's content and syncs no document-level ACLs. Admin-managed setup crawls every user's OneDrive with service credentials, and its document-level ACLs are always on and cannot be turned off.

## User-managed setup (console)

Guide the user through the [AWS Quick user-managed setup guide](https://docs.aws.amazon.com/quick/latest/userguide/onedrive-kb-user-managed.html). Each user signs in with their own Microsoft 365 account. If sign-in fails because the tenant restricts third-party apps, a Microsoft 365 administrator grants one-time admin consent for the AWS Quick app (see `<Definition - Knowledge Base Setup>` in SKILL.md and the guide).

## Admin-managed setup (console)

### Prerequisite checklist

Confirm each item with the admin one at a time. For any item that is missing, give the linked steps and wait for the admin to confirm it. The step-by-step setup is in the AWS Quick guide [Admin-managed setup (service credentials)](https://docs.aws.amazon.com/quick/latest/userguide/onedrive-kb-admin-managed.html) and the pages it links; the skill's own KMS key and certificate walkthrough is in [`../../assets/knowledge-base-auth-and-acl.md`](../../assets/knowledge-base-auth-and-acl.md).

1. **Roles.** AWS Quick administrator access, and administrator access in Microsoft Entra ID to register an app and grant API permissions.
1. **An AWS KMS asymmetric signing key** in `<quick-region>` (per `<Definition - Backend>` in SKILL.md): usage Sign and verify (`SIGN_VERIFY`), key spec `RSA_2048`, single-Region (multi-Region keys are not supported).
1. **A certificate that embeds the KMS public key** (not a standalone self-signed key pair), and its base64url SHA-1 thumbprint.
1. **An Entra app registration** with that certificate uploaded, the Microsoft Graph application permissions the guide lists, and admin consent granted.
1. **`kms:Sign` for AWS Quick on the key**, granted in the AWS Quick console under Manage account, Permissions, AWS resources, AWS Key Management Service (add the key ARN, then Finish and Save), not by editing the key policy.

### Values entered in the console

In the console Create knowledge base flow, the admin selects OneDrive and enters these values directly. OneDrive needs no `config` fields.

| Value | What it is |
|---|---|
| `client_id` | The Entra application (client) ID |
| `tenant_id` | The Entra directory (tenant) ID |
| `kms_key_arn` | The KMS signing key ARN, for example `arn:aws:kms:<quick-region>:123456789012:key/<key-id>` |
| `certificate_thumbprint` | The base64url SHA-1 thumbprint of the certificate |

To give other users access, the admin shares the knowledge base from its details page in the console ([To share an integration](https://docs.aws.amazon.com/quick/latest/userguide/integration-workflows.html#to-share-integration)).
