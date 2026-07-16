# Common Compliance Mistakes (Severity-Ranked)

Use when reviewing datasets for compliance gaps. Each entry gives the wrong pattern,
the correct pattern, the reason, and the severity.

1. Submitting a dataset without USUBJID.
   - Right: include USUBJID as a required variable in every SDTM and ADaM dataset.
   - Why: missing USUBJID breaks all cross-dataset joins. Severity: Critical.

2. Creating the DM domain without populating RFSTDTC.
   - Right: always populate RFSTDTC (reference start date) in DM from the first dose or randomization date.
   - Why: all study day (--DY) calculations depend on RFSTDTC. Severity: Critical.

3. Building ADSL without TRT01A/TRT01P variables.
   - Right: always include TRT01A (actual treatment) and TRT01P (planned treatment) in ADSL.
   - Why: no treatment assignment means no analysis population can be defined. Severity: Critical.

4. Creating a non-standard (custom) domain without documenting it in define.xml and the Reviewer's Guide.
   - Right: document all non-standard domains with full metadata in define.xml and explain the rationale in cSDRG.
   - Why: reviewers cannot interpret undocumented domains, causing review delays. Severity: High.

5. Placing standard SDTM variables (timing, result qualifiers, identifiers) in SUPPQUAL.
   - Right: use the parent domain's standard variables (--STDTC, --LOC, --METHOD, --GRPID) as defined in the Implementation Guide.
   - Why: triggers a P21 Error and signals poor domain mapping knowledge. Severity: High.

6. Omitting value-level metadata for BDS datasets with multiple PARAMCDs.
   - Right: include where-clause-based value-level metadata in define.xml for every PARAMCD in BDS datasets.
   - Why: missing value-level metadata is a P21 Error; define.xml is incomplete without it. Severity: High.

7. Using codelist values not present in the pinned controlled terminology version.
   - Right: pin one CT version at study start and use only values from that version, or document sponsor extensions for extensible codelists.
   - Why: triggers P21 Warning CT2003 and may delay regulatory review. Severity: Medium.

8. Recording dates with inconsistent precision across records (mixing full and partial dates without clear rules).
   - Right: define date precision rules in the SAP and apply consistent imputation logic documented in define.xml.
   - Why: inconsistent precision complicates imputation and introduces errors in study day calculations. Severity: Medium.
