---
description: "Google Drive knowledge base: what the backend accepts, the Google-side prerequisite checklist for admin-managed setup, the secret shape, and the enable_kb_integration call. Read it when setting up a Google Drive knowledge base."
last_updated: 2026-11-12
source_url: https://docs.aws.amazon.com/quick/latest/userguide/google-drive-knowledge-base.html
---

# Google Drive knowledge base

| Field | Value |
|---|---|
| Skill connector key | `google_drive` (the same key as the Google Drive action connector in [google-drive-action.md](google-drive-action.md)) |
| Suite | Google Workspace |
| Capability | Knowledge base |
| Admin-managed setup | Created through the backend: `enable_kb_integration` with `auth_type: "admin_managed"`. Document-level ACLs are always on. |
| User-managed setup | Console-only. Never call the backend for it. |
| Default secret name | `quick-admin-buddy/google-drive-kb-admin` (used when `secret_id` is omitted) |

For the current setup methods, prerequisites, and console steps, fetch the AWS Quick guide in this file's `source_url` and the pages it links (user-managed setup, admin-managed setup, Configure Google Workspace, and Creating a knowledge base in AWS Quick).

## Choosing the setup method

Recommend the method for `{org_size}` per `<Definition - Org Size Recommendation>` in SKILL.md, and the path per `<Definition - Knowledge Base Setup>`. The ACL difference to state when you present the choice: user-managed setup syncs no document-level ACLs (anyone with access to the knowledge base sees all its indexed content), while admin-managed setup always enforces them and the setting cannot be turned off. To change the ACL posture later, the knowledge base is recreated with the other method.

## User-managed setup (console)

Guide the user through the console steps in the [AWS Quick user-managed setup guide](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-user-managed.html); make no backend call. Each user signs in with their own Google account. If sign-in fails because the organization restricts third-party app access, a Google Workspace admin must allow the AWS Quick app first (see that guide's prerequisites).

## Admin-managed setup through the backend

The Google-side configuration is done by the admin in the Google Cloud console and the Google Workspace Admin console; the backend has no access there. Tell the admin openly that the skill can't do these steps for them, and that the skill creates the knowledge base once they are done.

### Prerequisite checklist

Confirm each item with the admin one at a time, per `<Workflow - Set Up Productivity Tools>`. For any item that is missing, give the admin the linked steps and wait for them to confirm it. The click-by-click steps for every item are in the AWS Quick guide [Configure Google Workspace](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-google-config.html).

1. **People and access.** A Google Workspace super administrator (Google requires one to configure domain-wide delegation) and permission to create a project in the Google Cloud console. The Google Workspace account's email domain must match the email domain of the AWS Quick identity ([admin-managed prerequisites](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-admin-managed.html)).
1. **A Google Cloud project with three APIs enabled:** Google Drive API, Google Drive Activity API, and Admin SDK API.
1. **A service account with a downloaded JSON key.** If key creation fails because the organization policy constraint `iam.disableServiceAccountKeyCreation` is enforced, an Organization Policy Administrator (`roles/orgpolicy.policyAdmin`, which is granted at the organization level) must allow key creation for the project. Steps: AWS Quick [Resolving organization policy restrictions](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-google-config.html#google-drive-kb-admin-troubleshooting-org-policy), and Google's [Allow service account key creation](https://docs.cloud.google.com/iam/docs/keys-create-delete), which states which organizations have the constraint on by default and recommends exempting only the projects that need keys. This changes the customer's Google Cloud governance, so the admin confirms it with their security owners. Treat the JSON key as a long-lived credential: keep it out of the chat and out of source control.
1. **Domain-wide delegation** in the Google Workspace Admin console, with Client ID = the service account's **Unique ID** and exactly these OAuth scopes, each a full URL:

   ```
   https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/drive.metadata.readonly,https://www.googleapis.com/auth/admin.directory.user.readonly,https://www.googleapis.com/auth/admin.directory.group.readonly,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/forms.body.readonly
   ```

   Steps: Google's [Control API access with domain-wide delegation](https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation). Wrong or incomplete scopes show up later as SSL certificate errors when the knowledge base is created ([AWS Quick troubleshooting](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-connection.html#google-drive-kb-admin-troubleshooting)).
1. **A dedicated delegated admin user** for the service account to impersonate, assigned the three prebuilt admin roles **Groups Reader**, **User Management Admin**, and **Storage Admin**. Its email address is the `admin_account_email`. Steps: Google's [Assign specific admin roles](https://knowledge.workspace.google.com/admin/users/assign-specific-admin-roles).

Continue only when the admin confirms they have the downloaded JSON key file and the delegated admin user's email.

### Build the secret

The secret's JSON body is the exact contents of the downloaded service-account key file plus one added key, `admin_account_email`. The backend requires `client_email`, `private_key`, and `admin_account_email`, and ignores the other key-file fields. The contract is in [`../../assets/auth-secret-contract.md`](../../assets/auth-secret-contract.md) (Google Drive knowledge base section).

- Name: the default `quick-admin-buddy/google-drive-kb-admin`, or a custom name that starts with `quick-admin-buddy/` (the only prefix the backend's execution role can read). Pass it as a name per Rule 9 in SKILL.md.
- Region: `<quick-region>`, per `<Definition - Backend>` in SKILL.md.

The admin runs this locally, with the downloaded file saved as `service-account.json`:

```bash
# Add admin_account_email to the downloaded key file, keeping every original key.
jq '. + {admin_account_email: "quick-kb-admin@example.com"}' service-account.json \
  > /tmp/gdrive-kb-secret.json

aws secretsmanager create-secret \
  --region <quick-region> \
  --name "quick-admin-buddy/google-drive-kb-admin" \
  --secret-string file:///tmp/gdrive-kb-secret.json

rm -f /tmp/gdrive-kb-secret.json   # remove the private key from disk
```

To update an existing secret, use `aws secretsmanager put-secret-value` with the full JSON.

### Create the knowledge base

Run `<Definition - Sharing Gate>` in SKILL.md to get the `owner`, then call:

```
enable_kb_integration {
  "connector_key": "google_drive",
  "auth_type": "admin_managed",
  "owner": "<owner username from the sharing gate>",
  "secret_id": "quick-admin-buddy/google-drive-kb-admin"
}
```

`secret_id` may be omitted when the secret has the default name. The backend reads the three fields from the secret and sends them inline as the data source's `Credentials.ServiceAccountCredentials` (`ClientEmail`, `ServiceAccountPrivateKey`, `AdminAccountEmail`), creates the `GOOGLE_DRIVE` data source, then creates the knowledge base crawling My Drive, shared drives, and files shared with users, with document-level ACLs on.

If the secret lacks a required field, the result is `validation_failure` with the missing keys in `data.missing_secret_fields`: fix the secret and retry. Branch on every other result per `<Definition - Result Status>` and `<Definition - Knowledge Base Cleanup>` in SKILL.md.

### Console alternative

The admin can also create the admin-managed knowledge base in the console with the same JSON key file and delegated admin email, following [Creating a knowledge base in AWS Quick](https://docs.aws.amazon.com/quick/latest/userguide/google-drive-kb-connection.html). Note for the admin that the connection name cannot be changed after it is saved.

## Limitations

File comments are not synchronized, with either setup method.
