# PA Request Parsing

Two inbound formats carry prior authorization (PA) requests: X12 278 (pipe-delimited
EDI segments) and the FHIR Da Vinci PAS Bundle (JSON with resource-typed entries).
Both parsers below use only the Python standard library, so they run in the Amazon
Quick `run_python` sandbox as well as in an external environment.

## Parse X12 278 Transaction

The X12 278 Health Care Services Review transaction carries PA requests and responses.
Segments are separated by `~` and elements within a segment by `*`.

```python
"""Parse X12 278 prior authorization request into structured dict."""
from dataclasses import dataclass, field


@dataclass
class PA278Request:
    member_id: str = ""
    provider_npi: str = ""
    diagnosis_codes: list[str] = field(default_factory=list)
    procedure_codes: list[str] = field(default_factory=list)
    service_date: str = ""
    quantity: int = 0
    place_of_service: str = ""


def parse_278(raw: str) -> PA278Request:
    """Parse X12 278 segments into a PA278Request."""
    req = PA278Request()
    segments = raw.replace("\n", "").split("~")
    for seg in segments:
        elements = seg.strip().split("*")
        seg_id = elements[0] if elements else ""
        if seg_id == "NM1" and len(elements) > 9:
            qualifier = elements[1]
            if qualifier == "IL":  # insured/member
                req.member_id = elements[9] if len(elements) > 9 else ""
            elif qualifier == "1P":  # provider
                req.provider_npi = elements[9] if len(elements) > 9 else ""
        elif seg_id == "HI":
            for el in elements[1:]:
                parts = el.split(":")
                if len(parts) >= 2:
                    code_qualifier, code = parts[0], parts[1]
                    if code_qualifier in ("ABK", "ABF"):  # ICD-10
                        req.diagnosis_codes.append(code)
        elif seg_id == "SV1" and len(elements) > 1:
            svc_parts = elements[1].split(":")
            if len(svc_parts) >= 2:
                req.procedure_codes.append(svc_parts[1])
        elif seg_id == "DTP" and len(elements) > 3:
            if elements[1] == "472":  # service date
                req.service_date = elements[3]
    return req
```

Key parameters: `NM1` qualifier `IL` is the member, `1P` is the provider. `HI` code
qualifiers `ABK`/`ABF` mark ICD-10 diagnosis codes. `DTP` qualifier `472` is the
service date. Gotcha: element indices are positional, so guard every access with a
length check as shown, since real 278 files omit trailing empty elements.

## Parse FHIR Da Vinci PAS Bundle

```python
"""Extract PA fields from a FHIR Da Vinci PAS Bundle."""
from dataclasses import dataclass, field


@dataclass
class PASRequest:
    member_id: str = ""
    provider_npi: str = ""
    diagnosis_codes: list[str] = field(default_factory=list)
    service_codes: list[str] = field(default_factory=list)
    supporting_info_types: list[str] = field(default_factory=list)


def parse_pas_bundle(bundle: dict) -> PASRequest:
    """Extract PA data from a FHIR PAS transaction Bundle."""
    req = PASRequest()
    resources = {
        entry["resource"]["resourceType"]: entry["resource"]
        for entry in bundle.get("entry", [])
        if "resource" in entry
    }
    # Patient / member
    patient = resources.get("Patient", {})
    for ident in patient.get("identifier", []):
        if ident.get("type", {}).get("coding", [{}])[0].get("code") == "MB":
            req.member_id = ident.get("value", "")
            break
    # Practitioner / provider NPI
    practitioner = resources.get("Practitioner", {})
    for ident in practitioner.get("identifier", []):
        if ident.get("system", "").endswith("/npi"):
            req.provider_npi = ident.get("value", "")
            break
    # Claim resource is the core of the PA request
    claim = resources.get("Claim", {})
    for dx in claim.get("diagnosis", []):
        coding = dx.get("diagnosisCodeableConcept", {}).get("coding", [])
        for c in coding:
            req.diagnosis_codes.append(c.get("code", ""))
    for item in claim.get("item", []):
        svc_coding = item.get("productOrService", {}).get("coding", [])
        for c in svc_coding:
            req.service_codes.append(c.get("code", ""))
    for info in claim.get("supportingInfo", []):
        cat_coding = info.get("category", {}).get("coding", [])
        for c in cat_coding:
            req.supporting_info_types.append(c.get("code", ""))
    return req
```

Key parameters: the member identifier uses type coding `MB`. The provider NPI is the
identifier whose `system` ends in `/npi`. The `Claim` resource holds diagnosis codes,
requested service codes (`productOrService`), and `supportingInfo` document categories.
Gotcha: build a `resourceType` map once, as shown, so you do not iterate the whole
bundle per field.

Both parsers return objects with the same core fields. Convert to a plain dict with
`dataclasses.asdict()` before passing to feature extraction (see
`references/feature-extraction.md`).
