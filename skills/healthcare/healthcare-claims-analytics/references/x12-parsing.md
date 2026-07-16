# X12 837 Professional Claim Parsing

## Inputs

A path to an X12 837P text file. The parser reads the segment terminator and element
separator from the interchange header, so it works regardless of which characters the
file uses.

## Code

```python
import pandas as pd
from typing import Generator


def parse_x12_837(filepath: str) -> Generator[dict, None, None]:
    """Parse an X12 837P file into claim records.

    Yields:
        dict with claim_id, charge_amount, place_of_service, dx_codes, proc_codes,
        provider_npi, member_id, service_date.
    """
    with open(filepath, "r") as f:
        content = f.read()

    seg_term = content[105] if len(content) > 105 else "~"
    elem_sep = content[3] if len(content) > 3 else "*"
    segments = content.split(seg_term)

    claim = {}
    for seg in segments:
        el = seg.strip().split(elem_sep)
        sid = el[0] if el else ""

        if sid == "CLM":
            if claim:
                yield claim
            claim = {
                "claim_id": el[1] if len(el) > 1 else None,
                "charge_amount": float(el[2]) if len(el) > 2 else 0.0,
                "place_of_service": el[5].split(":")[0] if len(el) > 5 else None,
                "dx_codes": [],
                "proc_codes": [],
            }
        elif sid == "HI" and claim:
            for e in el[1:]:
                parts = e.split(":")
                if len(parts) >= 2:
                    claim["dx_codes"].append(parts[1])
        elif sid == "SV1" and claim:
            pp = el[1].split(":") if len(el) > 1 else []
            claim["proc_codes"].append(
                {
                    "cpt": pp[1] if len(pp) > 1 else None,
                    "modifiers": [m for m in pp[2:6] if m] if len(pp) > 2 else [],
                    "charge": float(el[2]) if len(el) > 2 else 0.0,
                    "units": int(el[4]) if len(el) > 4 else 1,
                }
            )
        elif sid == "NM1" and claim:
            q = el[1] if len(el) > 1 else ""
            if q == "82":
                claim["provider_npi"] = el[9] if len(el) > 9 else None
            elif q == "IL":
                claim["member_id"] = el[9] if len(el) > 9 else None
        elif sid == "DTP" and claim:
            if len(el) > 1 and el[1] == "472":
                claim["service_date"] = el[3] if len(el) > 3 else None
    if claim:
        yield claim


# Usage
claims = pd.json_normalize(list(parse_x12_837("claims_837p.txt")))
```

## Key parameters

- Segment terminator: read from position 105 of the interchange, not hardcoded.
- Element separator: read from position 3 of the interchange, not hardcoded.

## Pitfalls

- Do not split segments on the newline character. The terminator can be `~`, `\n`, or any
  character; it is defined in the ISA header and assuming `~` breaks on other files.
