# Categorization Keywords

Keyword hints for assigning each outflow to exactly one category from the fixed
set. Matching is case-insensitive and substring-based against the transaction
description. Use these as guidance, not a closed list: apply judgment when a
merchant is well known but not listed. When two categories both plausibly match,
prefer the more specific one and mark the result low-confidence with `(?)`.

The fixed category set (assign every outflow to exactly one):
`Housing, Utilities, Groceries, Dining, Transport, Shopping, Subscriptions, Health, Insurance, Loan/Debt, Transfers, Fees, Cash/ATM, Other`.

| Category | Keyword hints |
|---|---|
| Housing | rent, mortgage, landlord, property mgmt, hoa, lease |
| Utilities | electric, power, gas company, water, sewer, internet, broadband, mobile, phone, telecom |
| Groceries | grocery, supermarket, market, foods, mart, aldi, kroger, tesco, safeway |
| Dining | restaurant, cafe, coffee, bar, pub, doordash, ubereats, deliveroo, mcdonald, pizza |
| Transport | fuel, gas station, petrol, uber, lyft, taxi, transit, metro, rail, parking, toll, airline, flight |
| Shopping | amazon, retail, store, shop, clothing, electronics, department |
| Subscriptions | netflix, spotify, hulu, disney, prime, membership, subscription, saas, patreon, youtube premium |
| Health | pharmacy, doctor, dental, clinic, hospital, medical, optic, gym, fitness |
| Insurance | insurance, assurance, policy, premium, geico, allstate |
| Loan/Debt | loan, credit card payment, repayment, financing, student loan, installment |
| Transfers | transfer, zelle, venmo, paypal, wire, ach, e-transfer, interac |
| Fees | fee, charge, service charge, overdraft, nsf, interest charge, maintenance fee |
| Cash/ATM | atm, cash withdrawal, cash advance, withdrawal |
| Other | anything that matches no hint above |

## Recurring detection

Flag a transaction group as recurring when all three hold:

1. Same or closely similar merchant/payee name (ignore trailing store numbers,
   dates, and reference codes).
2. Roughly regular cadence: weekly (about 7 days), monthly (about 28 to 31 days),
   or annual (about 365 days) gaps between occurrences.
3. Similar amount: within roughly 10 percent across occurrences, or identical.

Label each as `[subscription]` when it matches a Subscriptions keyword, otherwise
`[bill]`.
