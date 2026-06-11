---
name: job-to-invoice
display_name: "Instant Invoice"
icon: "💸"
description: "Create and send an invoice as soon as a job is complete. Use when the user says 'invoice the job', 'send invoice', 'bill the customer', 'get me paid', or describes completing work and needing to invoice. Built for field service businesses (plumbers, HVAC, landscapers, consultants) that need to invoice promptly after finishing work."
created_date: "2026-06-02"
last_updated: "2026-06-09"
tools: [recall_memories, save_to_memory, run_python]
depends-on: [quickbooks, gmail, outlook, paypal, scheduled_tasks]
inputs:
  - name: customer
    description: Customer name as it appears in QuickBooks (e.g., 'Johnson Residence', 'Acme Corp')
    type: string
    required: true
  - name: service
    description: Description of service performed or line items (e.g., 'Water heater replacement', '40 hours consulting at $150/hr')
    type: string
    required: true
  - name: amount
    description: Invoice total amount in dollars, or 'per quote' to pull from an existing quote/work order
    type: string
    required: true
  - name: terms
    description: Payment terms - net-15, net-30, due on receipt, etc.
    type: string
    required: false
    default: net-30
  - name: quote_ref
    description: Reference number of existing QuickBooks quote or estimate to pull line items from (optional)
    type: string
    required: false
  - name: payment_link
    description: "How this business's customers pay (a payment-page or invoice-pay URL, PayPal.me/Stripe link, Venmo/Zelle/Cash App handle, bank/ACH details, or a check mailing address / pay-by-phone contact). Used as the pay option in the invoice email when QuickBooks does not return its own pay link. Captured once on first use and remembered across ALL invoicing skills (Job-to-Invoice, Invoice Chaser, Deposit Collection). Never fabricated."
    type: string
    required: false
---

## Overview

Instant Invoice generates and sends a professional invoice from chat as soon as a job is complete. It pulls customer data and payment terms from QuickBooks, assembles the invoice, requests explicit owner approval, sends it to the customer with payment instructions, and schedules a follow-up reminder. It is built for field service businesses (plumbers, HVAC technicians, landscapers, consultants) that need to invoice promptly after finishing work, without switching between accounting software and email.

## Workflow

> **Intent guard.** A question or status check is NOT an instruction to act. If the
> owner is only asking (e.g. "how much would I invoice X for this?", "what's their
> email?", "do they have a deposit?"), answer or show a draft summary and STOP - do not
> create an invoice in QuickBooks and do not send anything. Creating and sending happen
> only after the explicit "Create it" (Step 4) and "Send" (Step 7) approvals. Default
> action is do-nothing.

> **Data handling safeguard.** Do NOT write customer content to the knowledge graph or
> long-term memory. Customer records, email addresses, invoice amounts, balances, line
> items, and anything pulled from a QuickBooks customer or invoice are read for the
> current task only and must never be persisted to the KG or memories. This prevents one
> customer's data from leaking into the user's context or a later session. The ONLY value
> this skill may store is the business owner's own reusable setting - their payment
> instruction (see Step 1) - which is the user's own data, not a customer's. When in
> doubt about whether something is the owner's setting or a customer's content, treat it
> as customer content and do not store it.

> **Source of truth and conflicts.** QuickBooks is the source of truth for customer
> records, amounts, terms, and tax status; these instructions govern behavior. If a
> stored memory conflicts with QuickBooks (for example a payment instruction that no
> longer matches), prefer the live QuickBooks data and surface the discrepancy to the
> owner rather than guessing. If following an instruction here would require storing
> customer content in the KG or memories, the safeguard above wins - do not store it, and
> proceed using the data in-task only.

### Step 1: Look Up Customer in QuickBooks
- **Mode**: `deterministic`
- **Tool**: `quickbooks__QueryEntities`
- **Params**: `{ "entity": "Customer", "query": "{{customer}}" }` - query the Customer entity by the name the user provided
- **Output**: Customer record including: display name, email address, billing address, default payment terms, and any open quotes/estimates
- **Also**: recall the business's saved payment instructions via `recall_memories` (query "business payment instructions for customer invoices" - a SHARED setting any invoicing skill may have saved, not Job-to-Invoice-specific) unless {{payment_link}} was provided; carry it forward for the email pay option in Step 7
- **Validate**: Customer found with a valid email address on file
- **On failure**: If no exact match, search with fuzzy matching and present top 3 results for the user to pick. If no results at all, ask the user for the customer's email so the invoice can still be sent.

### Step 2: Resolve Line Items and Amount
- **Mode**: `agentic`
- **Input**: `{{amount}}`, `{{service}}`, `{{quote_ref}}`, and the customer record from Step 1
- **Output**: Structured invoice line items (description, quantity, rate, amount) and total

**Logic:**
- If `{{quote_ref}}` is provided, pull line items from that QuickBooks estimate/quote directly - this avoids data re-entry and ensures accuracy.
- If `{{amount}}` is "per quote", search for the most recent open estimate for this customer and pull from there.
- Otherwise, parse `{{service}}` and `{{amount}}` into line items. Handle common patterns:
  - Simple: "AC install, $8200" → 1 line item
  - Hourly: "40 hours at $150/hr" → qty=40, rate=150, amount=6000
  - Multi-line (one customer): "Replaced heater and fixed leak, $450" → multiple line items on ONE invoice

- **Compute totals in code, not mentally.** Any line-item arithmetic (quantity × rate, "$X each" multiplication, summing line items into a total) MUST be done by generating and running code via `run_python`. Do not calculate totals in your head. Show the owner the computed figures so they can validate them.

- **"Each" vs "total":** when the owner says "$X each", multiply per unit/property (e.g. "3 properties at $150 each" = $150 per property, $450 total). When they say "$X total" or just "$X", treat it as the whole. If it is ambiguous which they mean, ask before proceeding - do not assume.
- **Batch / multiple recipients:** when the request names more than one customer or property ("invoice all three", "bill Elm St, Oak Ave, and Pine Rd"), this produces ONE invoice PER customer/property - not a single combined invoice (unless they explicitly ask for one). First, confirm the resolved list with the owner (names, each amount). Then run the rest of the workflow per invoice: each invoice gets its own create approval (Step 4) and its own email approval (Step 7) - never batch-create or batch-send without per-invoice gates. A single customer with several line items, by contrast, stays as ONE invoice.

- If `{{quote_ref}}` is provided or `{{amount}}` is "per quote", reconcile the pulled quote/estimate total against any stated `{{amount}}`. If they differ, do NOT silently pick one - surface both and ask the owner which is correct before proceeding.
- Amount sanity check (order-of-magnitude): if the resolved total is wildly out of line with this customer's history or the quote (for example 10x the quote, or an apparent extra zero), treat it as likely mis-keyed. HOLD - confirm the amount with the owner before creating or sending. Never create and email an invoice on an unconfirmed outlier amount.

- **Validate**: Total amount matches the quote (or the owner resolved any mismatch); line items are coherent; no unconfirmed outlier amount.
- **On failure**: If parsing is ambiguous or the quote and stated amount disagree, present the interpreted line items and both totals and ask the user to confirm before proceeding.

### Step 3: Determine Payment Terms
- **Mode**: `deterministic`
- **Input**: `{{terms}}` (user-provided or default), customer's default terms from QuickBooks
- **Output**: Final payment terms and due date

**Logic:**
- If user specified `{{terms}}`, use that.
- Otherwise use customer's default terms from QuickBooks.
- If neither exists, fall back to net-30.
- Calculate due date from today.

- **Validate**: Terms are a recognized format (net-15, net-30, net-60, due on receipt)
- **On failure**: Default to net-30 and note it in the approval summary.

### Step 3.5: Apply Sales Tax and Net Any Prior Deposit
- **Mode**: `agentic`
- **Tool**: `quickbooks__QueryEntities` (read customer tax status and any deposit/credit), then `run_python` for all arithmetic
- **Input**: Customer record (Step 1), line items (Step 2)
- **Output**: Tax-correct line items, the calculation, and the true balance due after any deposit

**Do the math in code, never in your head.** Any arithmetic in this step (subtotal, tax, deposit netting, balance due) MUST be computed by generating and running code via `run_python` - do not calculate amounts mentally or inline. After running it, show the owner the calculation it performed (the numbers and the steps: subtotal + tax - deposit = balance due) so they can validate it before approving in Step 4. Money math that the owner cannot check is not acceptable.

**Sales tax (ACCT-04A):**
- Read the customer's tax status (taxable vs. exempt) and the item/service taxability and tax code from QuickBooks via `quickbooks__QueryEntities`; apply the correct tax code so QuickBooks calculates tax on the invoice. Sales tax collected is a liability owed to the state, not revenue - invoicing tax-free by default under-collects it.
- If taxability or the jurisdiction's rate is ambiguous (mixed taxable materials and non-taxable labor, multi-jurisdiction, unclear exemption), ASK the owner in the approval step rather than defaulting to no tax. Never invent a tax rate.

**Prior deposit (ACCT-04B):**
- Check for an open customer deposit, prepayment, retainer, unapplied credit, or a deposit recorded against the related estimate/job. A deposit is unearned revenue (a liability) until the work is done; the final invoice must draw it down.
- If one exists, apply it as a credit/deposit line so the balance due is the net (total + tax - deposit). Do not bill the full amount when a deposit was already collected - that double-charges the customer.

- **Validate**: Tax code applied (or exemption confirmed); any prior deposit found is netted; the balance due was computed in code and shown to the owner; the balance due reflects total + tax - deposit
- **On failure**: If tax status cannot be determined, hold for owner confirmation in Step 4. If deposit data is unavailable, note that deposits were not checked and proceed on the gross, flagging it to the owner.

### Step 4: Present One-Click Approval
- **Mode**: `agentic`
- **Input**: All resolved data from Steps 1-3
- **Output**: Approval decision from user

Present a concise invoice summary for approval. This MUST be frictionless - the owner is in the field, possibly on mobile. Use a decision card:

```
**Invoice ready to create:**
- **To:** {{customer}} (customer_email)
- **For:** {{service description}}
- **Subtotal:** $X,XXX.XX
- **Sales tax:** $XX.XX ({{tax_code}}) - or "Tax-exempt" / "Confirm taxability"
- **Deposit applied:** -$X,XXX.XX (if a prior deposit exists)
- **Balance due:** $X,XXX.XX
- **Due:** [date] (net-30)
- **Payment:** the shared business payment instruction (from memory, or captured once if not yet saved). No QuickBooks/Intuit pay URL is added - the connector returns none, so a generated one would be fabricated.

<decision question="Create this invoice in QuickBooks?">
<option description="Create the invoice now - you'll review the email before it sends">Create it</option>
<option description="Let me fix something first (amount, tax, terms)">Edit</option>
<option description="Don't create">Cancel</option>
</decision>
```

If taxability is unknown or ambiguous (from Step 3.5), resolve it HERE before creating - ask "Should this be taxable?" rather than defaulting to no tax. This approval covers the invoice details and creating it in QuickBooks; the outbound email is reviewed separately in Step 7.

- **Validate**: User selects "Create it"; taxability is confirmed (not silently defaulted); any deposit is reflected in the balance due.
- **On failure**: If "Edit" - ask what to change, update, and re-present. If "Cancel" - stop workflow gracefully.

### Step 5: Create Invoice in QuickBooks
- **Mode**: `deterministic`
- **Tool**: `quickbooks__CreateInvoice`
- **Params**: `{ customer_id, line_items, payment_terms, due_date, tax_code, deposit_credit, memo }` - customer ID from Step 1, line items from Step 2, tax code and any deposit credit from Step 3.5, terms and due date from Step 3
- **Output**: Created invoice with invoice number and PDF link (the connector does not return a customer payment URL, so do not expect or invent one here)

**Include:**
- Line items from Step 2
- The sales-tax code / taxable status from Step 3.5 so QuickBooks calculates tax (or the confirmed exemption)
- Any prior deposit from Step 3.5 applied as a credit/deposit line so the balance due is net
- Payment terms from Step 3
- Payment link: prefer the shared business payment instruction from memory (key "business payment instructions for customer invoices", saved by any invoicing skill such as Invoice Chaser or Deposit Collection). If none is saved yet, ask the owner ONCE how customers pay (a link or portal, PayPal/Venmo/Zelle/Cash App, bank details, a phone number, or an email) and save it under that shared key so no invoicing skill asks again; substitute the invoice number into any placeholder. Do NOT add a QuickBooks or Intuit pay URL (no intuit.com / connect.intuit.com link): the QuickBooks connector has no get-invoice-share-link action, so any such URL the skill produces is fabricated and invalid. Never fabricate or hand-construct a payment link; if no saved instruction exists and the owner has not provided one, include a payment-contact line and say no online link was included.
- Memo: service description for customer's reference

- **Validate**: Invoice created successfully with a valid invoice number; tax applied per the confirmed status; deposit netted; no fabricated QuickBooks/Intuit pay URL is included (the connector returns none)
- **On failure**: If QuickBooks write fails (auth, validation), report the specific error to the user. Suggest they create manually and offer to copy the details to clipboard.

### Step 6: Attach Alternative Payment Link (Optional)
- **Mode**: `agentic`
- **Tool**: `paypal` connector (if connected)
- **Input**: Invoice amount, customer email
- **Output**: PayPal.me or PayPal invoice link

Only execute this step if PayPal connector is available. Generate a PayPal payment link as an alternative payment method to include in the email body.

- **Validate**: Valid PayPal link generated
- **On failure**: Skip silently - QuickBooks Payments link is sufficient.

### Step 7: Present Email Draft for Approval
- **Mode**: `agentic`
- **Input**: The created invoice (number, link, payment URL if any), the assembled email (subject + body), recipient
- **Output**: Owner approval of the outbound customer email

The invoice exists in QuickBooks now, but nothing has gone to the customer yet. Show the ACTUAL email that will be sent and get explicit approval before sending - approving the invoice in Step 4 is NOT approving the email. This is a customer-facing message and must never send unreviewed.

Every invoice email MUST give the customer a way to pay - never send an invoice with no payment path. Choose the pay option in this order:
1. The current QuickBooks connector does NOT return a customer payment link (it has no get-invoice-share-link action), so do NOT include any QuickBooks or Intuit pay URL - no intuit.com or connect.intuit.com links. Any such link the skill produces is fabricated and invalid; never invent one. Use a tool-provided URL only if a connector tool literally returns one in its result that you can point to.
2. Use the business's saved payment instruction ({{payment_link}} or the value recalled in Step 1) as the pay option - a payment page/link, PayPal.me/Stripe, Venmo/Zelle/Cash App, bank/ACH details, or a check address / pay-by-phone contact.
3. If neither exists (first time, nothing saved), ask the owner ONCE: "How should customers pay you? Paste a payment link or a payment contact and I'll put it on every invoice and remember it across all your invoicing skills." Record the owner's answer as a SHARED business memory so every invoicing skill reuses it, e.g. "Noted: the business's payment instructions for customer invoices are <value> (shared across invoicing skills - Invoice Chaser, Job-to-Invoice, Deposit Collection; do not re-ask)." Do not re-ask once it is saved here or by any sibling invoicing skill.
4. If the owner declines, include a payment-contact fallback ("To arrange payment, reply to this email or call us") and note no link was included.
Never fabricate or hand-construct a payment link. Show the chosen pay option in the draft below.

```
**Email ready to send to {{customer}} (customer_email):**
Subject: Invoice #[number] from [business name] - [service]

[The full body text as it will appear, including the payment link and due date]

<decision question="Send this email to the customer?">
<option description="Send it now AND set a follow-up reminder for [due + 3 days] in case it goes unpaid">Send + remind</option>
<option description="Send it now, no reminder">Send only</option>
<option description="Let me edit the message first">Edit</option>
<option description="Don't send - keep the invoice in QuickBooks only">Hold</option>
</decision>
```

- **Validate**: Owner picks Send + remind (default) or Send only. If they edit, use their exact wording. The email's pay option is the owner's saved payment instruction or a contact line - confirm it contains NO QuickBooks/Intuit URL (intuit.com / connect.intuit.com) unless a connector tool literally returned one; strip any such fabricated link before sending.
- **On failure**: If "Edit" - apply the change and re-present. If "Hold" - leave the invoice created in QuickBooks, do not email, and tell the owner they can send it later.

### Step 8: Send Invoice via Email
- **Mode**: `deterministic`
- **Tool**: the connected email connector - `outlook` or `gmail` (auto-detect which is available)
- **Input**: Customer email, invoice PDF attachment or link, payment link(s)
- **Output**: Sent email confirmation
- **Precondition**: Only run after the owner approved the email in Step 7. Never send an unreviewed customer email.
- **Then, in the SAME response:** if the owner chose "Send + remind" (the default), immediately carry out Step 9 (create the follow-up reminder) before writing any recap or "done" message. The send and the reminder are one action - do not end the turn, and do not show a confirmation, with the reminder still unset. If the owner chose "Send only", skip the reminder.

**Email content:**
- Subject: "Invoice #[number] from [business name] - [service]"
- Body: Brief professional message with invoice summary, payment link, and due date
- Attachment: Invoice PDF from QuickBooks (if available)
- Tone: Friendly, professional, brief - this is a service business, not a corporation

Use whichever email connector (Outlook or Gmail) is available.

- **Validate**: Email sent successfully (delivery confirmation from tool)
- **On failure**: If email fails, provide the invoice link for the user to share manually (text, WhatsApp, etc.)

### Step 9: Set Follow-Up Reminder (REQUIRED - do not skip)
- **Mode**: `deterministic`
- **Tool**: `create_scheduled_agent` (or a calendar tool as fallback)
- **Input**: Due date + 3 days, customer name, invoice number, amount
- **Output**: A scheduled reminder (or, if the owner chose "Send only", a noted skip)

This runs in the SAME response as the send (Step 8), driven by the owner's Step 7 choice - do not treat the sent email as the end of the workflow, and do not show the confirmation (Step 10) until this is resolved.

- If the owner chose "Send + remind" (the default): create the reminder now. Do NOT re-ask - they already approved it in Step 7.
- If the owner chose "Send only": skip, and note "no reminder set" in the confirmation.
- If somehow neither was captured (alternate entry): offer it in one tap ("Set a follow-up reminder for [due+3]? Set / Skip") rather than dropping it.

Create a one-time scheduled agent for [due date + 3 days]:
"Invoice #[number] for {{customer}} ($[amount]) was due [3 days ago]. Check QuickBooks; if still unpaid, follow up."
Scheduled agents run locally - they fire only when the machine is on and Quick is running; say so when confirming.

- **Validate**: A reminder/scheduled agent was created with the correct fire date, OR the owner chose "Send only". Never reach Step 10 with this unresolved.
- **On failure**: If the scheduled-agent tool fails, fall back to a calendar event. If that also fails, tell the owner the exact date to follow up manually and treat the step as resolved.

### Step 10: Confirmation
- **Mode**: `agentic`
- **Output**: Final confirmation message to user
- **Precondition**: Step 9 is resolved - the reminder was set or the owner explicitly skipped it.

Provide a brief, satisfying confirmation that states the reminder outcome:
```
✅ Invoice #1234 sent to customer@email.com
   Amount: $450.00 | Due: June 18
   Payment link included | Follow-up reminder set for June 21 (or: no reminder set)
```

Keep it short - the user is in the field and just wants confirmation it's done.

## Output

A sent invoice with:
1. Invoice created in QuickBooks (with number, PDF, payment link)
2. Email delivered to customer with payment link
3. Follow-up reminder scheduled at terms + 3 days
4. One-line confirmation to the owner

## Lessons Learned

### Do
- Keep each approval to ONE tap - a decision card, not a back-and-forth. There are TWO gates: the invoice details (before creating in QuickBooks) and the email (before it sends).
- Parse common field-worker shorthand: "$450", "per the quote", "40 hrs at 150"
- Confirm taxability before creating - a new customer or untaxed item is ambiguous; ask rather than invoicing tax-free (sales tax is a liability owed to the state, not revenue)
- Net any prior customer deposit/credit against the invoice so the customer is not double-charged
- Reconcile a pulled quote total against any stated amount; surface a mismatch instead of guessing
- Hold an order-of-magnitude outlier amount (likely an extra zero) for confirmation before creating or sending
- Show the balance due clearly in the approval so there are no surprises
- Always give the customer a way to pay - the business's saved payment method/contact (the QuickBooks connector does not return a pay link, so never add an intuit.com/connect.intuit.com URL). Capture it once and reuse across all invoicing skills (shared memory); never fabricate a link.
- Always close the loop on the follow-up reminder before finishing - sending the invoice is not the end. Offer it in one tap; never end the workflow with the reminder unaddressed.
- Use the customer's email from QuickBooks rather than asking the user for it

### Don't
- Don't require the user to specify line item structure formally - parse natural language
- Don't send the customer email without its own approval - approving the invoice is NOT approving the email
- Don't create the invoice in QuickBooks until after the invoice approval (avoid orphan invoices)
- Don't include a QuickBooks/Intuit payment URL (intuit.com, connect.intuit.com) - the connector can't produce one, so any such link is fabricated and invalid. Use the owner's saved payment instruction or a payment-contact line instead.
- Don't default to non-taxable silently
- Don't make the user pick between Gmail/Outlook - auto-detect which is connected
- Don't set overly aggressive follow-up timing (terms + 3 days is polite)

### Common Failures
- **Customer not found**: Fuzzy search first, ask user to pick from matches
- **QuickBooks write permission denied**: Guide user to reconnect with write scope
- **No email on customer record**: Ask user for email, proceed with manual entry
- **Amount parsing ambiguity**: "3 properties at $150" - confirm whether that's $150 total or $150 each
- **Quote reference not found**: Fall back to manual line items from user input

### When to Ask the User
- Customer name is ambiguous (multiple matches in QuickBooks)
- Amount or line item parsing is unclear
- No email address found for the customer
- Approval before sending (always - this is the core gate)
- If the user says "invoice all three" - confirm the list before batch processing