# SUPPQUAL Anti-Pattern Checklist

Use when deciding whether a collected field belongs in a Supplemental Qualifiers
(SUPPQUAL) dataset, the parent domain, or a custom domain.

## Never put in SUPPQUAL (move to parent domain or use a standard variable)

- Timing variables (--STDTC, --ENDTC, --DUR, --VISITNUM).
- Result qualifiers (--LOC, --LAT, --DIR, --METHOD).
- Standard identifiers (--GRPID, --REFID, --SPID).
- Any variable defined in the current SDTM Implementation Guide for that domain.

## Always appropriate for SUPPQUAL

- Free-text verbatim fields not fitting standard variables.
- Site-specific or country-specific collected fields.
- Non-standard data collected on the CRF with no Implementation Guide slot.
- Sponsor-defined flags needed for analysis traceability.

## Red flags indicating domain redesign is needed

- More than 5 SUPPQUAL records per subject per domain: consider a custom domain or FA.
- SUPPQUAL variable used in derivations: promote it to the parent domain.
- Same QNAM across more than 80 percent of subjects: this is a standard variable in disguise.

## SUPPQUAL formatting rules

- QNAM: 8 characters or fewer, unique within the parent domain.
- QLABEL: 40 characters or fewer.
- QORIG: one of CRF, DERIVED, ASSIGNED, PROTOCOL.
