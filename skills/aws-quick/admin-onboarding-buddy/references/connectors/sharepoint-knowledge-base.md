---
description: "Microsoft SharePoint Online knowledge base: what the backend accepts, the out-of-band prerequisite checklist for admin-managed setup, the secret keys, and the enable_kb_integration call. Read it when setting up a SharePoint knowledge base."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-knowledge-base.html
---

# Microsoft SharePoint knowledge base

| Field | Value |
|---|---|
| Skill connector key | `sharepoint` (the same key as the SharePoint action connector in [sharepoint-action.md](sharepoint-action.md)); required config `sites` |
| Suite | Microsoft 365 |
| Capability | Knowledge base |
| Admin-managed setup | Created through the backend: `enable_kb_integration` with `auth_type: "admin_managed"`, a `secret_id`, and `config.sites`. |
| User-managed setup | Console-only. Never call the backend for it. |
| Default secret name | `quick-admin-buddy/sharepoint-kb-admin` (used when `secret_id` is omitted) |

For the current setup methods, permissions, and console steps, fetch the AWS Quick guide in this file's `source_url` and the pages it links, in particular [Set up service credentials](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html).

## Choosing the setup method

Recommend the method for `{org_size}` per `<Definition - Org Size Recommendation>` in SKILL.md, and the path per `<Definition - Knowledge Base Setup>`. User-managed setup indexes only the signing-in user's content and syncs no document-level ACLs. Admin-managed setup crawls the named sites with service credentials and can enforce document-level ACLs. The ACL choice is fixed when the knowledge base is created; changing it means recreating the knowledge base.

The backend always creates an admin-managed SharePoint knowledge base with document-level ACLs on, so the Entra app needs the ACL-crawling permissions. If the admin wants a content-only (ACL off) admin-managed knowledge base, guide its creation in the console from [Create the knowledge base in AWS Quick](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-connection.html) with the same credentials.

## User-managed setup (console)

Guide the user through the [AWS Quick user-managed setup guide](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-user-managed.html); make no backend call. Each user signs in with their own Microsoft 365 account. If sign-in fails because the tenant restricts third-party apps, a Microsoft 365 administrator grants one-time admin consent for the AWS Quick app ([Admin consent for Microsoft 365](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-user-managed.html#sharepoint-kb-user-admin-consent)).

## Admin-managed setup through the backend

### Permission scope: all sites or `Sites.Selected`

The Entra app's permission scope decides how much of the tenant AWS Quick can read. The exact Microsoft Graph and SharePoint REST permissions for each combination are in the [AWS Quick permissions tables](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-config-permissions). Use one scope, not both.

- **All sites:** with ACL crawling, SharePoint REST `Sites.FullControl.All` plus Graph `Sites.Read.All`, `User.Read.All`, and `GroupMember.Read.All`. No per-site setup.
- **`Sites.Selected`:** the app reads only the sites explicitly granted to it. With ACL crawling: Graph `Sites.Selected`, `User.Read.All`, `GroupMember.Read.All`, and SharePoint REST `Sites.Selected`. Each site, including any site added later, needs its own grant with role `fullcontrol`.

Recommend `Sites.Selected` when the admin wants only some sites indexed, or cannot grant `Sites.Read.All` or `Sites.FullControl.All`. The `config.sites` value is the same for both scopes.

For the per-site grants, this skill recommends Graph Explorer, signed in as a SharePoint Administrator or Global Administrator who consents to `Sites.FullControl.All`; the temporary admin app in the AWS Quick guide is the fallback. Microsoft's [Create permission](https://learn.microsoft.com/en-us/graph/api/site-post-permissions) API reference documents the call and notes that, in a delegated call, the signed-in user must also be a member of the target site. The decision prompt and the step-by-step grant walkthrough are in [`../../assets/knowledge-base-auth-and-acl.md`](../../assets/knowledge-base-auth-and-acl.md).

### Prerequisite checklist

Confirm each item with the admin one at a time, per `<Workflow - Set Up Productivity Tools>`. For any item that is missing, give the linked steps and wait for the admin to confirm it. The step-by-step setup is in [Set up service credentials](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html); the skill's own walkthrough is in [`../../assets/knowledge-base-auth-and-acl.md`](../../assets/knowledge-base-auth-and-acl.md).

1. **Roles.** An AWS administrator for the KMS key, a Microsoft 365 Global Administrator or Privileged Role Administrator for the Entra app, a SharePoint Administrator or Global Administrator for `Sites.Selected` grants, and an AWS Quick administrator (Admin Pro) for the key grant.
1. **An AWS KMS asymmetric signing key** in `<quick-region>` (per `<Definition - Backend>` in SKILL.md): key type Asymmetric, usage Sign and verify (`SIGN_VERIFY`), key spec `RSA_2048`, single-Region (multi-Region keys are not supported). Record its ARN as `kms_key_arn` ([Step 1](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-step1-kms)).
1. **A certificate that embeds the KMS public key**, and its thumbprint as a base64url SHA-1 value (the JWT `x5t` form, which differs from the hexadecimal thumbprint the Entra portal shows). Record it as `certificate_thumbprint` ([Step 2](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-step2-certificate)).
1. **An Entra app registration** with the certificate uploaded, the application permissions for the chosen scope, and admin consent granted. Record its Application (client) ID as `client_id` and Directory (tenant) ID as `tenant_id` ([Step 3](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-step3-entra)).
1. **For `Sites.Selected` only, the per-site grants** for every site in `config.sites` (see the permission scope section above).
1. **`kms:Sign` for AWS Quick on the key:** in the AWS Quick console, Manage account, Permissions, AWS resources, AWS Key Management Service, add the key ARN, then Finish and Save. If the organization manages its own AWS Quick IAM service role, that role needs `kms:Sign` on the key instead ([Step 4](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-step4-iam)).

### Build the secret

The secret's JSON body has five keys. The contract is in [`../../assets/auth-secret-contract.md`](../../assets/auth-secret-contract.md) (SharePoint knowledge base section).

| Key | Value |
|---|---|
| `certificate_thumbprint` | The base64url SHA-1 thumbprint of the certificate |
| `kms_key_arn` | The KMS signing key ARN, for example `arn:aws:kms:<quick-region>:123456789012:key/<key-id>` |
| `tenant_id` | The Entra directory (tenant) ID |
| `client_id` | The Entra application (client) ID |
| `domain_url` | The SharePoint domain, for example `https://contoso.sharepoint.com`, or the custom SharePoint domain if the tenant uses one. The backend strips the scheme to the bare host the API needs. |

- Name: the default `quick-admin-buddy/sharepoint-kb-admin`, or a custom name that starts with `quick-admin-buddy/` (the only prefix the backend's execution role can read). Pass it as a name per Rule 9 in SKILL.md.
- Region: `<quick-region>`, per `<Definition - Backend>` in SKILL.md.

The backend reads these values and sends them inline on the data source, so the secret is read only by the backend's execution role.

### Create the knowledge base

Run `<Definition - Sharing Gate>` in SKILL.md to get the `owner`, then call:

```
enable_kb_integration {
  "connector_key": "sharepoint",
  "auth_type": "admin_managed",
  "owner": "<owner username from the sharing gate>",
  "secret_id": "quick-admin-buddy/sharepoint-kb-admin",
  "config": { "sites": [
    "https://contoso.sharepoint.com/sites/engineering",
    "https://contoso.sharepoint.com/sites/customer_support"
  ] }
}
```

`config.sites` is the list of SharePoint site URLs to index. `secret_id` may be omitted when the secret has the default name. The backend sends `certificate_thumbprint` and `kms_key_arn` as `SharePointClientCredentials`, and `tenant_id`, `client_id`, and the bare `domain_url` as `SharePointParameters`, then creates the knowledge base with the site list in both `dataEntityConfiguration.siteUrls` and `filterConfiguration.inclusionItemPaths` (the service requires both).

If the secret lacks a required key, the result is `validation_failure` with the missing keys in `data.missing_secret_fields`: fix the secret and retry. Branch on every other result per `<Definition - Result Status>` and `<Definition - Knowledge Base Cleanup>` in SKILL.md.
