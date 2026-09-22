---
description: "How transportation works after a placement option is confirmed: partnered Small Parcel and Less-Than-Truckload versus a non-partnered carrier, shipping modes, carrier mixing rules, void windows, bill of lading and pallets, tracking, and the source-address gotcha."
last_updated: "2026-09-15"
origin: original
---

# Carriers and Shipping

How transportation works after a placement option is confirmed, and what the seller must do per carrier type. From the Fulfillment Inbound (v2024-03-20) guides.

## The carrier choice (at the transportation gate)

Listing transportation options returns options with a shipping solution:

- Amazon Partnered Carrier (partnered): Amazon-negotiated rates; the quote is shown in the option.
  - Small Parcel Delivery: typically one tracking number per box.
  - Less-Than-Truckload (freight): palletized; the carrier provides a bill of lading.
- Use Your Own Carrier (non-partnered): the seller arranges and pays for shipping.

### Shipping modes (beyond Small Parcel and Less-Than-Truckload)
Options can carry more modes than just Small Parcel and Less-Than-Truckload: ground small parcel, freight, full truckload (palletized and non-palletized), ocean less-than-container and full-container, air small parcel, and air express. Present whatever the option list returns; do not assume only Small Parcel and Less-Than-Truckload exist.

### Mixing carriers across shipments
It is not strictly one carrier per plan. You can mix carrier selections across shipments (for example Small Parcel plus Less-Than-Truckload, or partnered plus non-partnered) only when the selections are on different shipping modes and all shipments are partnered-carrier-eligible. Outside those conditions, mixing returns an incompatible-carrier-mix error.

> Non-partnered carriers require a confirmed delivery window. For a non-partnered shipment you must confirm the anticipated delivery window before booking the fulfillment-center appointment, and before confirming transportation. For partnered carriers it is only needed when enrolled in the confirmed-delivery-window program.

## Amazon Partnered Carrier: Small Parcel Delivery

- The quote is in the transportation option.
- Void window: 24 hours after confirmation (charges may apply after).
- Amazon does not schedule pickup; the seller schedules pickup with the carrier directly.
- Tracking is provided automatically by the partnered carrier.

Tell the seller after confirm: schedule the carrier pickup; you have 24 hours to cancel free.

## Amazon Partnered Carrier: Less-Than-Truckload

- The freight-ready date must be within 2 weeks of workflow creation.
- Pallet information is required; check the pallet-listing operations.
- The carrier provides a bill of lading.
- Void window: 1 hour after confirmation (charges may apply after).
- For the India marketplace, a delivery challan document is available for partnered shipments.

## Non-Partnered Carrier (your own)

After confirming transportation, the seller ships and provides tracking, then you update the shipment tracking details:

- Small Parcel: a tracking number per box.
- Less-Than-Truckload or full truckload: the freight bill number or bill of lading number (one per shipment).

Constraints: this works only for shipments created via these API operations (not Seller Central created shipments), and one freight bill number per shipment.

## Cancellation windows (quote before cancelling)

| Carrier | Void window | After the window |
|---------|-------------|------------------|
| Amazon Partnered Small Parcel | 24 hours | Charges apply |
| Amazon Partnered Less-Than-Truckload | 1 hour | Charges apply |
| Non-Partnered | Any time | No charges |

## Source address change gotcha

Updating the shipment source address invalidates existing transportation options. The seller must regenerate and reconfirm transportation afterward.
