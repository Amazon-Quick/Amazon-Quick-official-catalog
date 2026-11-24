"""
description: Map the column names found in pasted tables to the canonical purchase and invoice review field names.
last_updated: 2026-11-24

Column synonym mapping for fpa-purchase-invoice-review (module name is skill-unique on purpose:
AWS Quick makes every skill's scripts importable by name, so a generic "columns" could collide).

map_col(raw_name) -> canonical column name
detect_table_type(columns) -> best-match type name, or 'unknown'
"""

import re

# canonical -> [synonyms (all lower-case; matched after normalizing to snake_case)]
SYNONYMS = {
    "id": [
        "id",
        "req_id",
        "req",
        "req_no",
        "req_num",
        "request_id",
        "request_no",
        "po_id",
        "item_id",
        "line_id",
        "pr_id",
        "pr_no",
        "request_number",
    ],
    "amount": [
        "amount",
        "total",
        "req_total",
        "po_total",
        "extended_amount",
        "ext_amount",
        "value",
        "net_amount",
        "line_amount",
        "extended",
        "line_total",
        "approval_amount",
    ],
    "vendor": ["vendor", "supplier", "vendor_name", "supplier_name", "payee"],
    "period": [
        "period",
        "quarter",
        "month",
        "fiscal_period",
        "posting_period",
        "posting_date",
        "fy_period",
        "acctg_period",
        "accounting_period",
    ],
    "cost_center": [
        "cost_center",
        "cc",
        "cost_ctr",
        "costcenter",
        "cost_centre",
        "cost_centre_code",
    ],
    "account": [
        "account",
        "gl",
        "gl_account",
        "gl_code",
        "account_no",
        "acct",
        "account_number",
        "gl_number",
    ],
    "justification": [
        "justification",
        "business_justification",
        "justification_text",
        "biz_justification",
        "narrative",
        "reason",
        "purpose",
        "description",
    ],
    "source": ["source", "plan_type", "budget_type", "plan_source"],
    "pooled": ["pooled", "pool", "is_pooled"],
    "status": ["status", "approval_status", "req_status", "po_status"],
    "unit_price": [
        "unit_price",
        "unit_cost",
        "price",
        "rate",
        "unit_rate",
        "rate_per_hour",
        "rate_per_hour_usd",
        "unit_price_usd",
    ],
    "qty": ["qty", "quantity", "units", "count", "po_qty", "po_hours"],
    "category": ["category", "type", "item_type", "spend_category"],
    "account_type": ["account_type", "acct_type", "type_code", "acct_class"],
    "item": [
        "item",
        "item_name",
        "product",
        "service",
        "sku",
        "material",
        "line_description",
        "item_description",
    ],
    "service_start": ["service_start", "start_date", "period_start", "from_date"],
    "service_end": ["service_end", "end_date", "period_end", "to_date", "thru"],
    "project": ["project", "project_code", "wbs", "project_id"],
    "useful_life_months": ["useful_life_months", "useful_life", "life_months"],
    "requester": ["requester", "requestor", "requested_by", "submitter", "raised_by"],
    "freight": ["freight", "shipping", "freight_amount"],
    "tax": ["tax", "tax_amount", "vat", "gst"],
    "contingency": ["contingency", "contingency_amount"],
    "invoice_no": [
        "invoice_no",
        "invoice_number",
        "invoice_num",
        "inv_no",
        "invoice",
        "invoice_id",
    ],
    "invoice_date": ["invoice_date", "inv_date", "date_invoiced"],
    "stated_total": ["stated_total", "invoice_total", "total_amount", "header_total"],
    "line": ["line", "line_no", "line_number"],
    "po": ["po", "po_no", "po_number", "purchase_order", "po_ref"],
    "sole_source_reason": [
        "sole_source_reason",
        "sole_source",
        "exception_reason",
        "exception",
    ],
    "quotes": ["quotes", "quotes_attached", "quote_count", "num_quotes"],
    "po_amount": ["po_amount", "committed_amount", "commitment", "open_amount"],
    "invoiced": ["invoiced", "invoiced_amount", "billed", "billed_amount"],
    "received": ["received", "received_qty", "qty_received_to_date"],
    "need_by": ["need_by", "need_by_date", "required_date", "delivery_date"],
    "contract_id": ["contract_id", "contract_no", "contract_number", "contract_ref"],
    "ceiling": ["ceiling", "contract_value", "not_to_exceed", "nte"],
    "auto_renew": ["auto_renew", "auto_renewal", "auto_renews"],
    "notice_days": ["notice_days", "notice_period_days", "cancellation_notice"],
    "valid_until": ["valid_until", "expiry_date", "valid_through", "good_through"],
    "qty_received": ["qty_received", "quantity_received", "goods_received_qty"],
    # One budget table with budget, actuals and open commitments side by side ("wide" budget).
    "budget_amount": [
        "budget",
        "budget_amount",
        "budgeted",
        "plan_amount",
        "budget_usd",
    ],
    "actual_amount": [
        "actuals",
        "actual",
        "actual_amount",
        "actuals_to_date",
        "spend_to_date",
        "spent",
        "actual_spend",
    ],
    "open_commitments": [
        "open_commitments",
        "commitments",
        "open_commitment",
        "committed",
        "open_pos",
        "open_po_amount",
        "encumbrances",
        "encumbered",
    ],
    "quote_id": ["quote_id", "quote", "quote_no", "quote_number", "quote_ref"],
}

_NORM = re.compile(r"[^a-z0-9]+")


def _n(s):
    return _NORM.sub("_", (s or "").strip().lower()).strip("_")


# Reverse map: normalized_synonym -> canonical
_REVERSE = {}
for _c, _syns in SYNONYMS.items():
    for _s in _syns:
        _REVERSE[_n(_s)] = _c


def map_col(raw_name):
    """Return canonical name for a raw column header, or normalized raw name if no match."""
    n = _n(raw_name)
    return _REVERSE.get(n, n)


# Table type detection: sets of canonical columns that identify each type.
# Requires at least 2 matching columns to avoid false positives.
# Order matters: on a tie the first entry wins (one exception: receipts and po_lines, below).
_SIGNATURES = {
    "requests": {"id", "amount", "vendor"},  # most common; must precede actuals
    "invoices": {"invoice_no", "vendor", "amount"},
    "po_lines": {"po", "line", "unit_price"},
    "receipts": {"po", "line", "qty_received"},  # keyed by po + line, like po_lines
    "contract": {"contract_id", "ceiling"},
    "rates": {"contract_id", "unit_price"},
    "budget_wide": {
        "cost_center",
        "account",
        "budget_amount",
        "actual_amount",
        "open_commitments",
    },
    "budget": {
        "cost_center",
        "source",
        "amount",
    },  # before actuals (source distinguishes)
    "actuals": {"cost_center", "account", "amount"},
    "commitments": {"po", "po_amount"},
    "lines_coding": {"id", "account", "account_type"},
    "quotes": {"id", "valid_until", "quote_id"},
    "history": {"item", "unit_price"},
    "items_summary": {"id", "amount", "status"},
}


def detect_table_type(columns):
    """Score column list against signatures; return best-match type or 'unknown'.

    Requires a score of at least 2 to return a typed result.
    A goods-receipt table (qty_received and no ordered qty) that ties with po_lines is receipts:
    read as po_lines it would be dropped and the 3-way match (INV-5) would silently not run.
    """
    col_set = set(columns)
    best_type, best_score = "unknown", 1  # threshold: score must beat 1
    scores = {}
    for ttype, sig in _SIGNATURES.items():
        score = scores[ttype] = len(sig & col_set)
        # A side-by-side budget table must have a budget column. Without this, a commitments
        # table (cost center, account, PO amount) scored as budget_wide and was split in three.
        if ttype == "budget_wide" and "budget_amount" not in col_set:
            score = scores[ttype] = 0
        if score > best_score:
            best_score, best_type = score, ttype
    if (
        best_type == "po_lines"
        and scores["receipts"] == best_score
        and "qty_received" in col_set
        and "qty" not in col_set
    ):
        best_type = "receipts"
    # An invoice table without a vendor column still has an invoice number: never read it as PO lines.
    if best_type == "po_lines" and "invoice_no" in col_set:
        best_type = "invoices"
    # A commitments table also carries cost center and account; the PO amount column decides it.
    if (
        best_type == "actuals"
        and "po_amount" in col_set
        and scores["commitments"] == best_score
    ):
        best_type = "commitments"
    # A quote table has supplier and amount like a request; a quote number or a validity date
    # decides it. A quote table that names its request (request_id maps to id) must still read
    # as quotes, or PRC-2..4 never see the quotes.
    if best_type == "requests" and (
        "valid_until" in col_set or ("quote_id" in col_set and "id" not in col_set)
    ):
        best_type = "quotes"
    return best_type
