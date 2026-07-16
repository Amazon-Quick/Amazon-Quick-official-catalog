# CMS Coverage Determinations

Reference data for Medicare National Coverage Determinations (NCD) and Local Coverage
Determinations (LCD), plus the master decision tree. Apply the decision tree internally;
present only the conclusion and its supporting evidence.

## NCD vs LCD

| Attribute | NCD (National) | LCD (Local) |
|-----------|----------------|-------------|
| Issuer | CMS central | Medicare Administrative Contractor (MAC) |
| Scope | All Medicare nationwide | MAC jurisdiction (A/B or DME) |
| Override | Cannot be overridden locally | Must comply with any applicable NCD |
| Appeal path | ALJ, then Medicare Appeals Council, then Federal court | Redetermination, then QIC, then ALJ |
| Update frequency | Infrequent (years) | More frequent (annual review) |

An LCD cannot contradict or override an NCD. Always check for an applicable NCD first.

## LCD Evaluation Checklist

When assessing whether a service is covered under an LCD:

- Identify the MAC jurisdiction for the provider's location.
- Search the CMS Medicare Coverage Database for active LCDs.
- Check the LCD's ICD-10 code list: is the patient's diagnosis included?
- Review the "Indications and Limitations" section for clinical criteria.
- Verify the CPT/HCPCS code is listed as covered under the LCD.
- Check for any associated billing article with documentation requirements.
- Confirm no superseding NCD exists for the same service.

LCDs are jurisdiction-specific. Coverage rules from one MAC have no authority in another.

## Master Decision Tree: PA Request Evaluation

```
Is the service on the payer's PA-required list?
- NO  -> No PA needed; proceed with service.
- YES
  - Is there an applicable NCD?
    - YES -> Does the request meet NCD criteria?
      - YES -> Approve (document NCD compliance).
      - NO  -> Deny (cite NCD; appeal to ALJ if Medicare).
    - NO  -> Check for LCD or plan-specific policy.
      - LCD exists  -> Evaluate LCD criteria.
      - Plan policy -> Evaluate plan criteria.
        - Medical necessity met?
          - YES -> Check step therapy.
            - Step therapy satisfied     -> Approve.
            - Step therapy NOT satisfied
              - Exception applies?  -> Approve with exception.
              - No exception        -> Deny (cite step therapy).
          - NO  -> Deny (cite medical necessity).
        - Documentation incomplete? -> Pend for additional information.
```
