# FHIR Da Vinci PAS Implementation

Reference data for the Da Vinci Prior Authorization Support (PAS) Implementation Guide,
a FHIR-based workflow for submitting and tracking prior authorization requests. CMS
mandates payer support by 2026.

## PAS Workflow Sequence

1. The provider EHR constructs a PAS `Bundle` with a `Claim` plus supporting resources.
2. The EHR submits the `$submit` operation to the payer's PAS endpoint.
3. The payer returns a `ClaimResponse` with a disposition: `approved`, `denied`, or `pended`.
4. If pended, the payer may request additional info via a `CommunicationRequest`.
5. The provider submits an updated `Bundle` with the requested documentation.
6. The payer issues a final `ClaimResponse`.
7. The provider queries the `$inquire` operation for status updates.

## Documentation Best Practice

Structure clinical documentation in the `supportingInfo` field using proper FHIR resource
references. Unstructured PDF attachments cannot be processed by automated adjudication
systems and cause delays.

## References

- https://build.fhir.org/ig/HL7/davinci-pas/en/
