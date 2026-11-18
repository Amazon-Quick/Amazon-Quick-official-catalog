---
description: "Knowledge base setup methods (user-managed and admin-managed), the user-managed and admin-consent guidance, the service-credential prerequisites for SharePoint, OneDrive, and Google Drive (KMS key, certificate, Entra permissions, Sites.Selected grants), and document-level ACL guidance, read in Step 5 when the admin sets up a knowledge base."
last_updated: 2026-11-12
origin: original
---

# Knowledge base authentication and document-level ACLs

Knowledge bases use a different authentication model from action connectors:
the action connector OAuth methods are not valid for a knowledge base. A
knowledge base has two setup methods:

| Method | Name in the AWS Quick console | Who it indexes | Document-level ACLs |
|---|---|---|---|
| `user_managed` | User-managed setup | Only the content the signing-in user can access | No |
| `admin_managed` | Admin-managed setup (service credentials) | Every user's content across the organization | OneDrive and Google Drive: always on. SharePoint: on or off, chosen at creation. |

Which of these the skill creates through the backend, and which it guides in
the console, is set by `<Definition - Knowledge Base Setup>` and Rule 7 in
`SKILL.md`: admin-managed `sharepoint` and `google_drive` are created with
`enable_kb_integration`; user-managed setup, `onedrive`, and `confluence` are
console-only. This file adds the setup detail behind that table.

> ### What the backend does for an admin-managed knowledge base (two-step create)
>
> `enable_kb_integration` with `auth_type: "admin_managed"` makes two AWS Quick
> API calls in order: first a data source (`CreateDataSource`, which holds the
> source connection and service credentials), then the knowledge base
> (`CreateKnowledgeBase`, which references the data source by ARN). The skill
> makes one tool call; the backend runs both. If the second call fails, follow
> `<Definition - Knowledge Base Cleanup>` in `SKILL.md`.
>
> | Connector key | Required `config` | Secret (`secret_id`) |
> |---|---|---|
> | `sharepoint` | `sites` (list of site URLs to index) | `certificate_thumbprint`, `kms_key_arn`, `tenant_id`, `client_id`, `domain_url`; default name `quick-admin-buddy/sharepoint-kb-admin` |
> | `google_drive` | None | The downloaded service-account JSON plus `admin_account_email`; default name `quick-admin-buddy/google-drive-kb-admin` |
>
> A missing `config` field is reported in `data.missing_config_fields`. The
> secret JSON for each is in
> [`auth-secret-contract.md`](./auth-secret-contract.md). For OneDrive, the same
> four certificate values are entered in the console instead (Rule 7). For
> Confluence, see
> [`../references/connectors/confluence-knowledge-base.md`](../references/connectors/confluence-knowledge-base.md).

Sources: AWS Quick User Guide,
[OneDrive knowledge base](https://docs.aws.amazon.com/quick/latest/userguide/onedrive-knowledge-base.html),
[SharePoint knowledge base](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-knowledge-base.html),
[Google Drive knowledge base](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-knowledge-base.html),
[Best practices for managing ACLs](https://docs.aws.amazon.com/quick/latest/userguide/acl-best-practices-kb.html).
*Content was rephrased for compliance with licensing restrictions.*

## How to help the admin choose

Which method to recommend, and in what order to list the options, follows
`<Definition - Org Size Recommendation>` and Rule 14 in `SKILL.md`, using the
`{org_size}` already asked. Ask one question and state the trade-off plainly.
Present the recommended option first. For a large organization:

```
<decision question="How should this knowledge base authenticate and scope access?">
<option description="Recommended for your organization size. Uses service credentials (an Entra app and certificate for Microsoft, or a Google service account with domain-wide delegation). Indexes every user's content across the organization and enforces document-level ACLs where the source supports them, so each user sees answers only from documents they can access.">Admin-managed setup (service credentials)</option>
<option description="Not recommended for your organization size: it depends on one person's sign-in and access. You sign in to the source yourself, and it indexes only the content your own account can see. No document-level ACLs: everyone who can use the knowledge base can see all of its indexed content.">User-managed setup</option>
</decision>
```

For a small organization:

```
<decision question="How should this knowledge base authenticate and scope access?">
<option description="Recommended for your organization size. You sign in to the source yourself. Indexes only the content your own account can see. No document-level ACLs: everyone who can use the knowledge base can see all of its indexed content.">User-managed setup</option>
<option description="Uses service credentials (an Entra app and certificate for Microsoft, or a Google service account with domain-wide delegation). Indexes every user's content across the organization and enforces document-level ACLs where the source supports them.">Admin-managed setup (service credentials)</option>
</decision>
```

Act on the answer per `<Definition - Knowledge Base Setup>`: user-managed is
guided in the console ("Guide the user" below); admin-managed goes to the
backend for `sharepoint` and `google_drive` once the service credentials are in
place, and to the console for `onedrive`.

Facts to give with either choice (from the AWS Quick User Guide):

- Admin-managed crawls every user's content in the organization. Document-level
  ACLs keep each user to what they can access in the source.
- User-managed indexes only what the signing-in user can access and has no
  document-level ACLs, so anyone who can use the knowledge base can retrieve
  everything indexed in it.

**SharePoint scope.** When the admin wants admin-managed SharePoint for only
some sites, or cannot grant `Sites.Read.All` or `Sites.FullControl.All`, offer
least-privilege `Sites.Selected` as its own question before setting up the
service credentials:

```
<decision question="How much of SharePoint should the AWS Quick app be able to read?">
<option description="The app reads all SharePoint sites in the tenant. No per-site grants. Uses Sites.Read.All, or Sites.FullControl.All for ACL crawling.">All sites (default)</option>
<option description="The app reads only the sites you grant. Least privilege. Uses Sites.Selected and needs a per-site permission grant for each site, including any site added later.">Only specific sites (Sites.Selected)</option>
</decision>
```

On `Sites.Selected`, follow "SharePoint admin-managed: tenant-wide vs. per-site
(`Sites.Selected`)" below. The `config.sites` value passed to
`enable_kb_integration` is the same either way: the scope changes only how the
Entra app is permissioned.

## What each method needs

- **`user_managed`:** an interactive provider sign-in that only the user can
  complete in the AWS Quick console, so the skill guides it and makes no backend
  call. It is per-user and self-service: it indexes one signing-in user's
  content with that user's credentials and sets up nothing for the rest of the
  organization. Each user who needs their own content indexed sets it up
  themselves.

### Guide the user: create a user-managed knowledge base in the console

The user does this, signed in to AWS Quick with their own account. The AWS
Quick guides for each source are
[SharePoint](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-user-managed.html),
[OneDrive](https://docs.aws.amazon.com/quick/latest/userguide/onedrive-knowledge-base.html),
and [Google Drive](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-user-managed.html).

1. In the AWS Quick console, choose **Knowledge** in the left navigation.
2. Under **Set up new knowledge base**, find the source (**Microsoft SharePoint
   Online**, **Microsoft OneDrive**, or **Google Drive**) and choose the **+**
   (Add) icon.
3. On the **Authentication method** step, choose the sign-in option (for
   example **Sign in to SharePoint** or **Sign in to Google Drive**).
4. Complete the provider sign-in with their own credentials and accept the
   requested permissions. The browser must allow popups from the AWS Quick
   console domain.
5. Enter a **Name** (and optional description), then under **Content** choose
   **Add content** and select what to index. Only content their account can
   access is shown.
6. Choose **Create**. An initial sync starts automatically.

Remind them: user-managed indexes only their own accessible content and has no
document-level ACLs.

### Admin consent / third-party app access (when sign-in is blocked)

No admin step is needed in the normal case. The exception is an organization
that restricts third-party app access:

- **Microsoft 365 (OneDrive, SharePoint):** if the tenant restricts third-party
  app access, the user sees an error instead of the consent dialog, and a
  Microsoft 365 administrator must grant one-time admin consent for the AWS
  Quick app. After that, every user in the organization can connect. Flag this
  for Microsoft sources and offer to walk the admin through it. The AWS Quick
  guide, [Admin consent for Microsoft 365](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-user-managed.html#sharepoint-kb-user-admin-consent),
  gives both paths: a Global Administrator or Privileged Role Administrator
  selects **Consent on behalf of your organization** in the Microsoft sign-in
  dialog during the AWS Quick flow, or grants consent for the AWS Quick
  enterprise application in the Microsoft Entra admin center. The application
  name is the one shown in the consent dialog. For the Entra clicks, see
  Microsoft's
  [Grant tenant-wide admin consent to an application](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent);
  to check whether the tenant restricts user consent, see
  [Configure how users consent to applications](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-consent).
- **ACL-enabled Microsoft knowledge bases** use a separate AWS Quick-managed
  Entra application for real-time access checks, which needs its own consent if
  the organization requires admin consent. The AWS Quick console gives a direct
  consent link when ACLs are enabled. See the AWS Quick guide
  [Document-level access controls (SharePoint)](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-acl.html).
- **Google Workspace (Google Drive):** if the organization restricts
  third-party app access, a Google Workspace administrator must allow the AWS
  Quick app before users can sign in. See the AWS Quick
  [prerequisites](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-user-managed.html#google-drive-kb-user-managed-prereqs)
  and Google's
  [Control which apps access Google Workspace data](https://knowledge.workspace.google.com/admin/apps/control-which-apps-access-google-workspace-data).

## What admin-managed needs

- **SharePoint and OneDrive (Microsoft 365):** an AWS KMS signing key, a
  certificate that embeds the KMS public key (the private key never leaves
  KMS), and a Microsoft Entra app registration with that certificate uploaded
  and the Microsoft Graph and SharePoint application permissions granted with
  admin consent. AWS Quick guides:
  [SharePoint service credentials](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html)
  and
  [OneDrive service credentials](https://docs.aws.amazon.com/quick/latest/userguide/onedrive-kb-admin-config.html).
  - **OneDrive** (ACLs always on): Microsoft Graph application permissions
    `Files.Read.All`, `Sites.Read.All`, `User.Read.All`, `Group.Read.All`, and
    `GroupMember.Read.All`.
  - **SharePoint:** the permissions depend on scope and on ACL crawling; see
    "SharePoint admin-managed: tenant-wide vs. per-site (`Sites.Selected`)"
    below.
- **Google Drive (Google Workspace):** a Google Cloud service account with
  read-only API access and domain-wide delegation, plus a dedicated admin user
  for the service account to impersonate (its email is `admin_account_email` in
  the secret). AWS Quick guide:
  [Admin-managed Google Drive knowledge base setup](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-admin-managed.html).
  For the Google Admin console steps, see Google's
  [Control API access with domain-wide delegation](https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation)
  and
  [`../references/connectors/google-drive-knowledge-base.md`](../references/connectors/google-drive-knowledge-base.md).

#### Prerequisite: create the AWS KMS asymmetric signing key (SharePoint/OneDrive)

Admin-managed SharePoint and OneDrive sign their OAuth client assertions to
Microsoft Entra with an AWS KMS asymmetric signing key. The private key never
leaves KMS; only the public key is exported and embedded in the certificate
uploaded to Entra. Create the key before the knowledge base, because its ARN is
one of the four certificate values: for SharePoint it goes in the secret as
`kms_key_arn`; for OneDrive the admin enters it in the console's Create
knowledge base flow. Source:
[Set up service credentials, Step 1](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-kms-configure).

Create it in `<quick-region>` (the Region rule is in `<Definition - Backend>`
in `SKILL.md`). In the KMS console (Customer managed keys, **Create key**), on
**Configure key**:

| Setting | Value |
|---|---|
| Key type | Asymmetric |
| Key usage | Sign and verify |
| Key spec | RSA_2048 |
| Key material origin | KMS (recommended) |
| Regionality | Single-Region (multi-Region keys are not supported) |

Give it an alias (for example `quick-sharepoint-service-auth`), skip to review,
and **Finish**. Record the key ARN: it is needed for the certificate, the
knowledge base (`kms_key_arn`), and the AWS Quick grant below.

AWS CLI equivalent, for the admin to run:

```bash
aws kms create-key \
  --key-spec RSA_2048 \
  --key-usage SIGN_VERIFY \
  --description "AWS Quick SharePoint/OneDrive service auth signing key" \
  --region <quick-region>
# then, optionally, an alias:
aws kms create-alias \
  --alias-name alias/quick-sharepoint-service-auth \
  --target-key-id <key-id-from-create-key> \
  --region <quick-region>
```

> The key administrator and key usage pages can stay at their defaults: AWS
> Quick is granted access separately (next paragraph), not through the key
> policy at creation time.

After the key exists, generate the certificate from its public key (next
subsection), register the Entra app and upload the certificate, then grant AWS
Quick access to the key.

**Grant AWS Quick access to the KMS signing key in the AWS Quick console, not
by editing the key policy.** This is a prerequisite before
`enable_kb_integration` for SharePoint and before the console create for
OneDrive. In AWS Quick, choose **Manage account**, then **Permissions**, **AWS
resources**; scroll to **AWS Key Management Service**, select the checkbox,
choose **Select keys**, enter the KMS key ARN, choose **Add**, then **Finish**
and **Save**. This needs the AWS Quick administrator (Admin Pro) role. Source:
[Step 4: Grant AWS Quick permission to the KMS key](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-step4-iam).

> **Exception:** if the organization manages its own AWS Quick IAM service role,
> that role needs `kms:Sign` on the signing key instead of the console grant.

#### Certificate: embed the KMS public key (KMS-backed signing)

The certificate must embed the KMS key pair's public key, so its public key
matches the KMS private key. Follow
[Step 2: Generate a self-signed certificate](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-step2-certificate)
in the AWS Quick guide (OpenSSL 3.0 or later and the AWS CLI). In outline:
export the KMS public key with `aws kms get-public-key`, create a CSR with a
temporary local key, issue the certificate with OpenSSL's `-force_pubkey`
pointing at the KMS public key, convert it to DER (`certificate.cer`), and
upload that to the Entra app registration.

- **Expected OpenSSL warning:** OpenSSL reports that the signature key and the
  certificate's public key do not match. This is expected: the certificate is
  signed with the temporary local key but contains the KMS public key.
- **Thumbprint format:** `certificate_thumbprint` is the base64url-encoded
  SHA-1 of `certificate.cer`
  (`openssl dgst -sha1 -binary certificate.cer | base64 | tr '+/' '-_' | tr -d '='`),
  not the hexadecimal thumbprint the Entra portal shows.

### SharePoint admin-managed: tenant-wide vs. per-site (`Sites.Selected`)

For an admin-managed SharePoint knowledge base, the Entra app's permission
scope decides how much of the tenant AWS Quick can reach. Offer the choice when
the admin wants only certain sites or cannot grant tenant-wide access. All
permissions are application permissions, split across two APIs. Source:
[Permissions](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-config-permissions).

| Scope | ACL crawling | Microsoft Graph | SharePoint REST | Per-site grant |
|---|---|---|---|---|
| All sites (default) | Off (content only) | `Sites.Read.All` | `Sites.Read.All` | None |
| All sites (default) | On | `Sites.Read.All`, `User.Read.All`, `GroupMember.Read.All` | `Sites.FullControl.All` | None |
| `Sites.Selected` | Off (content only) | `Sites.Selected` | `Sites.Selected` | One per site |
| `Sites.Selected` | On | `Sites.Selected`, `User.Read.All`, `GroupMember.Read.All` | `Sites.Selected` | One per site, role `fullcontrol` |

- ACL crawling needs full control because the SharePoint REST API requires it to
  read site-level and item-level permission assignments.
- Pick one scope: the AWS Quick guide says not to combine the all-sites and
  `Sites.Selected` permissions on the same app.
- **Trade-off to state:** all sites needs no per-site grants but gives the app
  read access to every SharePoint site in the tenant. `Sites.Selected` limits
  the app to the sites granted, but every site needs its own grant, including
  any site added to the knowledge base later; a newly added site without a
  grant returns nothing.

> **OneNote caveat:** OneNote crawling (`Notes.Read.All`) is not supported in
> admin-managed setup, because Microsoft Graph's OneNote API does not support
> app-only authentication (see Microsoft's
> [OneNote API overview](https://learn.microsoft.com/en-us/graph/integrate-with-onenote)
> and the AWS Quick
> [Permissions](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-config-permissions)
> note). For OneNote content, use user-managed setup.

#### Guide the admin: grant per-site access for `Sites.Selected`

The app registration (certificate, `Sites.Selected` permissions, admin consent)
is the same as in the all-sites flow; only the permissions chosen and the
per-site grants differ.

> **Prerequisite: admin role (check first).** The per-site grant needs a
> SharePoint Administrator or Global Administrator; Teams Administrator and
> most other roles get `accessDenied`. The AWS Quick guide lists Microsoft 365
> Global Admin for this step, and Microsoft's
> [Create permission](https://learn.microsoft.com/en-us/graph/api/site-post-permissions)
> reference requires SharePoint Administrator or higher for delegated calls.
> Role names and template IDs are in Microsoft's
> [Entra built-in roles](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference).

> **Prerequisite: KMS signing-key access.** Grant AWS Quick access to the KMS
> key in the AWS Quick console as described above, before
> `enable_kb_integration`.

**Grant role:** use `fullcontrol` when ACL crawling is on (as in the AWS Quick
guide), and `read` for content only. Both are site permission roles in
Microsoft's
[Selected permissions overview](https://learn.microsoft.com/en-us/graph/permissions-selected-overview).

For each site, the grant is a Microsoft Graph
`POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions` call with
this body, where `<role>` is `fullcontrol` or `read` and the application id and
name are those of the AWS Quick app registration (not of any helper app):

```json
{
  "roles": ["<role>"],
  "grantedToIdentities": [
    { "application": { "id": "<AWS Quick app client id>", "displayName": "<AWS Quick app name>" } }
  ]
}
```

Repeat per site; a site added to the knowledge base later needs its own grant.
Ways to make the call:

- **AWS Quick guide path (temporary admin app):** follow
  [Step 3b: Grant site-level permissions](https://docs.aws.amazon.com/quick/latest/userguide/sharepoint-kb-admin-config.html#sharepoint-kb-admin-sites-selected).
  It gets each Site ID from `https://{tenant}.sharepoint.com/sites/{SiteName}/_api/site/id`,
  creates a temporary Entra app with Microsoft Graph `Sites.FullControl.All`
  (application) and a client secret, gets a client-credentials token, posts the
  grant, and then deletes the temporary app. The grants persist after the app is
  deleted, and AWS Quick never sees that app.
- **Graph Explorer:** an administrator signed in to
  [Graph Explorer](https://learn.microsoft.com/en-us/graph/graph-explorer/graph-explorer-overview)
  and consented to `Sites.FullControl.All` can resolve the site id
  (`GET https://graph.microsoft.com/v1.0/sites/{hostname}:/sites/{site-path}`),
  post the grant above, and confirm it with
  `GET https://graph.microsoft.com/v1.0/sites/{site-id}/permissions`. Microsoft
  notes that write requests in Graph Explorer act on the signed-in tenant's
  data.
- **PnP PowerShell (scripting):** PnP PowerShell requires the organization to
  register its own Entra application; follow
  [Register an Entra ID Application to use with PnP PowerShell](https://pnp.github.io/powershell/articles/registerapplication.html).

Then create the knowledge base with the AWS Quick app's client ID, tenant ID,
certificate thumbprint, KMS key ARN, and SharePoint domain URL, as in the
all-sites flow.

## Document-level ACLs (admin-managed)

ACLs are always on for admin-managed OneDrive and Google Drive. For
admin-managed SharePoint, AWS Quick makes ACLs optional (chosen at creation),
but the backend always creates it with ACLs on; a content-only (ACL off)
SharePoint knowledge base is created in the console. AWS Quick syncs identity and
permission changes from the source on the knowledge base refresh schedule
(every 24 hours by default), enforces them on every retrieval, and, for
supported integrations, also checks document access against the source in real
time. If it cannot evaluate a document's permissions for a query, it returns no
documents rather than unfiltered results. Source:
[Best practices for managing ACLs in knowledge bases](https://docs.aws.amazon.com/quick/latest/userguide/acl-best-practices-kb.html).

Help the admin set ACLs up:

1. **Confirm the integration supports document-level ACLs.** OneDrive,
   SharePoint, and Google Drive admin-managed knowledge bases do.
2. **Keep source permissions as the source of truth.** ACLs are read from the
   source (sharing and group membership), so set access there.
3. **Know the resolution scope.** AWS Quick resolves ACLs within the namespace
   of the knowledge base creator, and treats email addresses as
   case-insensitive.
4. **Choose a refresh schedule** that meets the organization's access-change
   needs; the default is every 24 hours.
5. **Assign at least one additional owner** to an admin-managed knowledge base,
   so it stays manageable if its creator leaves. `share_kb_integration` grants
   VIEWER only (Rule 6 in `SKILL.md`), so add a co-owner in the AWS Quick
   console.
6. **Test with representative users** before sharing the knowledge base
   broadly.
7. **On personnel changes,** update source permissions, then refresh the
   knowledge base before the email address is reassigned.

Limitations to relay:

- **ACL configuration is permanent.** ACLs cannot be turned on for a knowledge
  base created without them, nor off once on; recreate the knowledge base to
  change it.
- **Sharing the knowledge base and document ACLs are separate controls.**
  Sharing decides who may use the knowledge base; ACLs limit which indexed
  documents each of those users can retrieve. Review both. The share offer
  itself is `<Definition - Sharing Gate>` in `SKILL.md`.
- ACL-enabled knowledge bases are not compatible with Quick Research; for
  research, create a separate knowledge base without ACLs.
- For users in very large groups, ACL propagation can lag behind a completed
  sync; allow time before treating missing content as an access issue.
