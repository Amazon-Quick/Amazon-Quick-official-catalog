---
description: "Detailed method for <Workflow - Set Up Extensions>: offering the Office add-ins or browser extension for the suite and recording admin-attested status."
last_updated: 2026-11-12
origin: original
---

# Step 6: Set up AWS Quick extensions

**Mode:** guided (console or install, no backend create call). **Entry:** from
Step 5 after action connectors and knowledge bases are set up, with `{suite}`
set. **Next:** Step 7 (integration testing).

## Goal

Guide the admin to install the AWS Quick **extensions** for their productivity
`{suite}`, and **record each extension's status in the backend**
(`list_extensions` and `set_extension_status`). Extensions bring AWS Quick into
the apps people already use. The user does the **actual install** (Microsoft
add-ins from the Office add-in store or deployed by a Microsoft 365 admin; the
browser extension from the browser's web store). There is no AWS Quick admin API
to create or verify an extension, so the backend records an **admin-attested**
status (`installed`, `skipped`, or `not_configured`), not an API-verified one.
The skill presents the right set for `{suite}`, explains what each unlocks,
links the official install guide, and persists the admin's decision so it
appears in the onboarding summary.

> Extensions are **client-side add-ins**, independent of the action connectors
> and knowledge bases from Step 5. They surface AWS Quick inside an app or
> browser; they do not create AWS Quick integrations themselves. Offer them
> after the connectors and knowledge bases so the admin already has something
> for the extensions to talk to.

## List the extensions for the suite (backend)

Start by listing the extensions the backend tracks for `{suite}` and their
current status:

```
quick-admin-buddy-runtime-target___list_extensions
  { }          # uses the tenant's stored suite; or pass {"suite": "microsoft_365"}
```

The result's `data.extensions` is the suite-filtered set, each with `key`,
`display_name`, `docs_url`, `description`, and `status` (`installed`, `skipped`,
or `not_configured`). Offer only the ones returned: Microsoft add-ins for
Microsoft 365 and the browser extension for Google Workspace. The backend
enforces the suite gate and rejects a mismatched `set_extension_status`.

## Branch on `{suite}`

### 4.1 Microsoft 365: offer all four Microsoft extensions

When `{suite}` is `microsoft_365`, offer **all four** Microsoft Office
extensions, one at a time:

| # | Extension | `extension_key` | What it unlocks | Official guide |
|---|---|---|---|---|
| 1 | **Microsoft Outlook extension** | `outlook_addin` | AWS Quick inside Outlook (email and calendar context) | https://docs.aws.amazon.com/quick/latest/userguide/outlook-extension.html |
| 2 | **Microsoft Excel extension** | `excel_addin` | AWS Quick inside Excel workbooks | https://docs.aws.amazon.com/quick/latest/userguide/excel-extension.html |
| 3 | **Microsoft Word extension** | `word_addin` | AWS Quick inside Word documents | https://docs.aws.amazon.com/quick/latest/userguide/word-extension.html |
| 4 | **Microsoft PowerPoint extension** | `powerpoint_addin` | AWS Quick inside PowerPoint decks | https://docs.aws.amazon.com/quick/latest/userguide/powerpoint-extension.html |

### 4.2 Google Workspace: offer the browser extension

When `{suite}` is `google_workspace`, offer the **browser extension** (this flow
has no Google app add-ins):

| Extension | `extension_key` | What it unlocks | Official guide |
|---|---|---|---|
| **Browser extension** | `browser_extension` | AWS Quick in the browser alongside Google Workspace web apps | https://docs.aws.amazon.com/quick/latest/userguide/browser-extension.html |

## Per-extension loop

Do one extension per turn. For Microsoft 365 go in order 1 to 4; for Google
Workspace there is just the browser extension.

### 1. Offer the extension

```
<decision question="Would you like to install the {extension name} now?">
<option description="Install this extension for AWS Quick">Yes, walk me through it</option>
<option>Skip for now</option>
</decision>
```

On **skip**, record it as skipped (step 3) and move to the next extension (or
to Step 7 if none remain). On **yes**, continue.

### 2. Guide the install

- Open the extension's **official guide** (its `docs_url` from `list_extensions`,
  also linked above) and summarize its install steps for the admin in a few
  lines rather than pasting the whole page.
- **Microsoft add-ins:** an organization-wide rollout is usually done by a
  Microsoft 365 administrator through centralized deployment in the Microsoft
  365 admin center
  ([Microsoft: Deploy Office Add-ins in the Microsoft 365 admin center](https://learn.microsoft.com/en-us/microsoft-365/admin/manage/manage-deployment-of-add-ins)),
  while an individual user can add it from the app's add-in store. Flag that
  admin deployment may be required if the tenant restricts user-installed
  add-ins.
- **Browser extension:** it is installed per browser from that browser's web
  store, and the user signs in to AWS Quick inside the extension.
- Confirm the admin has completed the install before recording it. The install
  is a client-side action the backend cannot verify, so the status is the
  admin's attestation.

### 3. Record the status in the backend

Persist the admin's decision so it shows up in the onboarding summary. The
status is **admin-attested**, not API-verified.

- Admin confirmed it's installed: `installed`.
- Admin chose to skip: `skipped`.

```
quick-admin-buddy-runtime-target___set_extension_status
  {
    "extension_key": "<outlook_addin|excel_addin|word_addin|powerpoint_addin|browser_extension>",
    "status": "<installed|skipped>"
  }
```

Branch on `Result_Status`:

- **`success`**: confirm using `message`, then move to the next extension.
- **`validation_failure`**: the backend says what to fix:
  - an unknown `extension_key` returns `data.valid_extensions`;
  - an invalid `status` returns `data.valid_statuses` (`installed`, `skipped`,
    `not_configured`);
  - a suite mismatch returns `data.suite_gate` and `data.stored_suite` (an
    extension not valid for the tenant's suite was offered; offer only what
    `list_extensions` returned).

Then move to the next extension.

## Exit criteria

- Each extension for `{suite}` was offered individually (all four for Microsoft
  365; the browser extension for Google Workspace), and the admin either
  installed it (guided to the official guide) or explicitly skipped it.
- Each decision was **recorded in the backend** with `set_extension_status`
  (`installed` or `skipped`), so it appears in `get_onboarding_summary` and
  `get_tenant_configuration` under `extensions`.
- Proceed to [Step 7: Integration testing and report](step-7-integration-testing.md).
