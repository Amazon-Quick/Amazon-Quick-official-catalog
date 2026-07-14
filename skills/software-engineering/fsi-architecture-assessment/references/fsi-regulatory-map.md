# FSI Use Case Regulatory Map and Common Gaps

Reference data for contextualizing an assessment. Use it to map a stated use case to its
typical regulatory regime and architecture requirements, and to check for the gaps that
recur in FSI workloads. This is lookup data, not a rule: confirm jurisdiction and data
classification with the user when they are not evident.

## Use Case to Regulation Mapping
| Use Case | Primary Regulations | Key Architecture Requirements |
|----------|--------------------|-------------------------------|
| Payment Processing | PCI-DSS, PSD2 | Tokenization, network segmentation, audit logging |
| Trading | MiFID II, Dodd-Frank, SEC | Low-latency, order audit trail, market data resilience |
| Fraud Detection | AML/KYC, BSA | Real-time inference, model explainability, alert management |
| Lending or Underwriting | ECOA, FCRA, Fair Lending | Model governance, bias detection, decision audit trail |
| Core Banking | Basel III, SOX | Multi-Region disaster recovery, data sovereignty, transaction integrity |
| Insurance Claims | Solvency II, HIPAA | Data privacy, claims automation governance, reserving accuracy |
| Gen AI or Agentic AI | SR 11-7, EU AI Act | Model risk management, human oversight, guardrails, prompt security |

## Typical FSI Requirements by Use Case
- Payment processing: PCI-DSS, real-time availability, transaction integrity.
- Fraud detection: low-latency inference, model explainability, audit trails.
- Trading platforms: ultra-low latency, market data resilience, regulatory reporting.
- Lending and underwriting: fair lending compliance, model governance, data lineage.
- Insurance claims: data privacy, document processing, automated decision governance.
- Core banking: 24/7 availability, data sovereignty, disaster recovery.
- Gen AI and Agentic AI: model risk management, prompt security, human oversight, guardrails.

## Common Architecture Gaps in FSI Workloads
- Missing encryption at the application layer (only in-transit and at-rest present).
- Single-Availability-Zone deployments for critical workloads.
- Lack of automated compliance checking (manual audit processes).
- Missing AI model governance for Gen AI components.
- No defined RTO or RPO targets validated through testing.
- Insufficient network segmentation between environments.
- Missing automated incident response for AI or agent failures.
- No cost-to-value tracking for AI inference workloads.
