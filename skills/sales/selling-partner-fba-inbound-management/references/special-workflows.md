---
description: "Two variants of the standard FBA inbound pipeline: the Pack Later flow for unknown carton contents (Less-Than-Truckload only) and the India marketplace flow (skip packing options, manage compliance, book self-ship appointments)."
last_updated: "2026-09-15"
origin: original
---

# Special Workflows: Pack Later and India

Two variants of the standard pipeline. Detect them up front and adjust.

## Pack Later (unknown carton contents, Less-Than-Truckload only)

When: the seller does not yet know exact box contents at plan-creation time. Small Parcel Delivery is NOT available for Pack Later; Less-Than-Truckload (freight) only.

How it differs from pack-first:

| Step | Pack First | Pack Later |
|------|-----------|-----------|
| Set packing information | full box contents (items per box) | box dimensions and weight only, no items |
| Content information source | box content provided | 2D barcode or manual process |
| When items are assigned to boxes | before placement | after placement is confirmed |
| Shipping mode | Small Parcel or Less-Than-Truckload | Less-Than-Truckload only |

Sequence: create the inbound plan, generate/list/confirm placement, set packing information (dimensions and weight only), generate/list/confirm transportation, then the seller provides actual box contents later (Seller Central scan and pack, spreadsheet upload, or web form).

Tell the seller: this uses the Pack Later (Less-Than-Truckload) flow; you will set boxes with dimensions and weight now and add item-level contents later in Seller Central.

## India marketplace

India has extra requirements and one omission:

- Skip packing-option generation; it is not supported for India.
- Compliance must be managed:
  - Check what is needed per merchant SKU (item compliance details, read).
  - Set the compliance information (item compliance details, write).
- Self-ship appointments are required for fulfillment-center drop-off:
  - Generate appointment slots (provide a date range).
  - Retrieve the generated slots.
  - Book a slot (decision gate; let the seller pick).
  - Cancel a slot if needed (requires a reason comment).
- Delivery challan: a delivery challan document is available for partnered shipments.

Tell the seller: for an India fulfillment center we will check compliance first, skip packing-option generation, and after transportation is set, book a drop-off appointment.
