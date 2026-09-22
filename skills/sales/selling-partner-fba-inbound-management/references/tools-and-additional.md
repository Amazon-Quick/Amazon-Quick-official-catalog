---
description: "Additional FBA inbound functionality (labels, prep, delivery windows, shipment content updates), the modify and cancel operations, read-only inspection operations, key constraints, and common errors for the Fulfillment Inbound pipeline."
last_updated: "2026-09-15"
origin: original
---

# Additional Functionality, Operation Reference, Errors and Constraints

## Additional functionality

Labels (FNSKU): create marketplace item labels; ask for marketplace, merchant SKUs plus quantities, label type, page type, and locale. For shipment or box labels, the shipment id you pass must be the shipmentConfirmationId (returned after confirming the placement option), not the pre-confirm shipmentId.

Prep: read the prep owner (seller or Amazon) and prep types per merchant SKU, and set who handles prep and labeling. US note: from January 1, 2026 sellers must prep and label all products themselves for the US marketplace, so set the prep owner and label owner to the seller accordingly.

Delivery windows: generate, list, then confirm the delivery window (a decision gate). Mandatory for non-partnered carriers; confirm before booking the fulfillment-center appointment and before confirming transportation. For partnered carriers, only when enrolled in the confirmed-delivery-window program.

Shipment content updates (modify box contents after transportation is confirmed): generate content-update previews, review the item changes and cost impact, then confirm the content-update preview (a decision gate that accepts the changes and any added cost).

## Modify and cancel operations

| Action | Notes |
|--------|-------|
| Rename plan | any time |
| Rename shipment | any time |
| Update source address | invalidates transportation options; regenerate |
| Update box identifiers | custom IDs shown on box labels |
| Update tracking | non-partnered only, after transport confirmed |
| Cancel plan | voids all shipments; warn about charges and void window first |
| Cancel appointment | India only; requires a reason comment |

## Inspection and reading (read-only)

Read the plan top-level status, list all plans, get a full shipment (including the transportation selection), and check async operation status. Read contents with the item, box, and pallet listing operations at the plan and shipment level, and the packing-group listing operations. India: read item compliance details, self-ship appointment slots, and the delivery challan document. Content updates: get and list the content-update previews. Use the shipment-item listing to generate a pick list per shipment once placement is confirmed.

## Key constraints

| Constraint | Detail |
|-----------|--------|
| Carrier mixing | Allowed across shipments only on different shipping modes with all shipments partnered-carrier-eligible; otherwise it errors |
| Packing before placement | Set packing info first; editing box info after placement means you must regenerate placement options |
| Transportation inputs | Generating transportation options needs a ready-to-ship date and a confirmed ship-from address; collect them from the seller |
| Delivery window (non-partnered) | Mandatory; confirm before the fulfillment-center appointment and before confirming transportation |
| Label shipment id | Use the shipmentConfirmationId, not the pre-confirm shipmentId |
| Multiple expiration dates per SKU | Not supported on one inbound plan; use separate plans |
| Placement is permanent | Once confirmed, cannot be changed for the plan |
| Confirm packing in 24 to 72 hours | Packing groups expire otherwise |
| 500K units per SKU | Max per inbound plan |
| Case-packed not supported | Use Send to Amazon in Seller Central |
| Older shipments not accessible | Only current-flow plans are visible |
| Pack Later is Less-Than-Truckload only | Small Parcel not available for unknown-carton flows |
| Partnered Less-Than-Truckload freight-ready | Within 2 weeks of workflow creation |
| US prep and label (January 1, 2026) | Sellers must self-prep and label for US; set prep owner and label owner to the seller |
| Source address update | Invalidates transportation options |
| Non-partnered tracking | API-created shipments only; one freight bill per shipment |

## Common errors

| Error | Cause | Resolution |
|-------|-------|-----------|
| Incompatible carrier mix | Mixing carriers outside the allowed conditions | Mixing is allowed only on different shipping modes with all shipments partnered-carrier-eligible; otherwise use one carrier |
| Operation FAILED | Async processing error | Read the error message, fix the input, retry |
| Packing options not generating | India marketplace | Skip; not supported for India |
| Cannot update tracking | Shipment created via Seller Central | Only API-created shipments are supported |
| Transportation options empty | Source address changed | Regenerate transportation options |
| Placement confirmation fails | Invalid or expired option | Regenerate placement options |

## Seller vs Vendor

This workflow is for Sellers (3P) only. Vendors (1P) use a separate Direct Fulfillment workflow.
