# Decline and gateway error categories

Look up the category a decline code or gateway message falls into, then read across
for the plain meaning, whether it is typically a hard or soft decline, who should act,
the recommended action, and retry guidance. Codes are processor specific and issuers
often mask the true reason, so treat every mapping as the common interpretation, not a
definitive ruling. Processor examples are illustrative, not exhaustive.

## Category reference

### card data error
- Plain meaning: The submitted card details are wrong or inconsistent (bad number, wrong expiry, failed AVS or postal code, wrong CVV).
- Decline type: soft (the data can be corrected and re-submitted).
- Who acts: merchant or customer.
- Action: correct the card number, expiry, CVV, or billing address, then re-submit.
- Retry guidance: retry after fixing the data, not before.
- Processor examples: Stripe `incorrect_number`, `invalid_expiry_year`, `incorrect_cvc`; Authorize.net response reason 6, 7, 8; ISO code 14 (invalid card number).

### insufficient funds
- Plain meaning: The card is valid but the account lacks available funds or credit.
- Decline type: soft.
- Who acts: customer.
- Action: ask the customer to use another payment method or retry later; for recurring charges, schedule a retry within network rules.
- Retry guidance: safe to retry later, but cap attempts to respect network retry rules.
- Processor examples: Stripe `insufficient_funds`; ISO code 51 (insufficient funds); Authorize.net response reason 2 or 3 in some configurations.

### issuer decline (generic)
- Plain meaning: The issuing bank declined without a specific reason. Often intentionally vague to avoid revealing account state.
- Decline type: hard or unknown (often treated as hard).
- Who acts: customer, via their issuing bank.
- Action: ask the customer to contact their card issuer; guidance is general because the issuer gives no detail.
- Retry guidance: do not blindly retry; a fresh authorization only helps if the customer resolves it with their bank.
- Processor examples: "Do Not Honor" ISO code 05; Stripe `do_not_honor`, `generic_decline`; ISO code 12 (invalid transaction).

### fraud / risk block
- Plain meaning: The processor, issuer, or a risk engine flagged the transaction as potentially fraudulent.
- Decline type: hard.
- Who acts: customer via issuer, or merchant reviewing risk rules.
- Action: do not bypass or weaken fraud controls; the customer should contact their issuer, and the merchant should review legitimate-but-blocked patterns through the processor's risk tools.
- Retry guidance: do not retry blindly; repeated attempts can escalate risk scoring.
- Processor examples: Stripe `fraudulent`, `lost_card`, `stolen_card`, `pickup_card`; ISO codes 04, 07, 41, 43.

### expired / invalid card
- Plain meaning: The card has expired or the card number is not a valid, active card.
- Decline type: hard for the presented card; soft if a valid replacement exists.
- Who acts: customer (merchant if a card-updater service is available).
- Action: ask the customer to update to a current card; for subscriptions, prompt a card update.
- Retry guidance: do not retry the same card; retry only after the card is updated.
- Processor examples: Stripe `expired_card`, `invalid_account`; ISO code 54 (expired card), 14 (invalid card number).

### authentication (3DS / SCA)
- Plain meaning: The transaction requires or failed customer authentication such as 3-D Secure or Strong Customer Authentication.
- Decline type: soft (can succeed once authentication completes).
- Who acts: merchant (enable or trigger authentication) and customer (complete the challenge).
- Action: enable or route the payment through 3-D Secure and have the customer complete the challenge.
- Retry guidance: retry through an authenticated flow, not as a plain re-charge.
- Processor examples: Stripe `authentication_required`; ISO code 1A (additional customer authentication required); Adyen "Authentication required" or refused with a 3DS reason.

### processor / config error
- Plain meaning: The problem is in the account or gateway configuration, not the card (wrong credentials, disabled processing, unsupported currency, account not fully activated).
- Decline type: not a card decline; a setup or account issue.
- Who acts: merchant.
- Action: check gateway credentials, account activation status, enabled payment methods, currency support, and merchant category settings.
- Retry guidance: do not retry until the configuration is corrected.
- Processor examples: Stripe `processing_error`, API key or account errors; Authorize.net response reason 13 (merchant account not active), 103 (invalid credentials).

### network / timeout
- Plain meaning: A transient communication failure between the gateway, processor, and issuer; the outcome may be unknown.
- Decline type: soft.
- Who acts: merchant (system) and processor.
- Action: retry once after a short delay using idempotency to avoid double charges; if it persists, check processor status.
- Retry guidance: a single guarded retry is appropriate; avoid rapid repeated retries.
- Processor examples: Stripe `processing_error` on timeout; ISO code 91 (issuer or switch inoperative), 96 (system malfunction).

## Widespread failure checks

When many transactions fail at once rather than one card, suspect an account or
configuration cause rather than the cards:
- Verify API keys and credentials are current and not rotated or revoked.
- Confirm the merchant account is active and not under review or hold.
- Check enabled payment methods, supported currencies, and country restrictions.
- Confirm 3-D Secure or SCA routing is configured for regions that require it.
- Check the processor's status page for an outage.
- Review recent changes to fraud or risk rules that may over-block.
