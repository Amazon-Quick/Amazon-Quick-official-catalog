# ADaM Rules, define.xml Value-Level Metadata, and SDTM Versions

Use for Analysis Data Model (ADaM) compliance, define.xml content planning, and
minimum standard version questions.

## SDTM version requirements by agency

| Agency        | Minimum SDTM | Minimum IG | Notes                              |
|---------------|--------------|------------|------------------------------------|
| FDA           | 3.3          | 3.3        | Required for NDA/BLA since 2017     |
| PMDA          | 3.2          | 3.2        | Accepts 3.3; 3.4 encouraged         |
| EMA           | 3.2          | 3.2        | Not yet mandatory but recommended   |
| Health Canada | 3.3          | 3.3        | Aligned with FDA                    |

## ADaM rules (non-obvious)

1. Traceability is mandatory. Every derived variable must trace to SDTM via SRCDOM, SRCVAR, SRCSEQ.
2. DTYPE flags derived records. Imputed or derived records (LOCF, WOCF) require DTYPE.
3. AVAL and BASE must share units. CHG = AVAL minus BASE is meaningless otherwise.
4. Value-level metadata is required for BDS where variable attributes differ by PARAMCD. define.xml must include where clauses for each parameter.
5. Computational methods are required for every derived variable in define.xml.

## define.xml value-level metadata for BDS datasets

For Basic Data Structure (BDS) datasets, define.xml must specify per PARAMCD:

- Origin (CRF versus Derived), which may differ by parameter.
- Data type and length. AVAL is always numeric, but AVALC length varies.
- Codelist reference, only for parameters with categorical AVALC.
- Computational method, the derivation algorithm specific to that PARAMCD.
- Where clause, the condition identifying which records the metadata applies to.

Missing value-level metadata is a Pinnacle 21 Error for any BDS dataset with more
than one PARAMCD.
