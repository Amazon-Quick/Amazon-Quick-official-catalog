# FSI Lens Pillar Assessment Checklists

Best-practice questions for assessing an architecture against the AWS Well-Architected
Financial Services Industry (FSI) Lens across the six pillars. Each question maps to an
FSI Lens best practice. Cite the pillar and the specific practice by name when recording a gap.

## Operational Excellence
- Is there a documented operational planning approach (Three Lines of Defense model)?
- Are infrastructure and application deployments automated (Infrastructure as Code, CI/CD)?
- Is there automated governance (account management, budget controls, compliance automation)?
- AI workloads: Are there model risk management frameworks, human-in-the-loop validation, and AI model versioning and rollback strategies?
- Agentic AI: Are there dedicated governance structures, specialized monitoring, and lifecycle management for autonomous agents?

## Security
- Is Security by Design implemented with pre-tested security templates?
- Is encryption enforced for data at rest, in transit, and at the application level?
- Are access controls following least-privilege principles?
- Is there network segmentation with defense-in-depth?
- AI workloads: Are there model governance frameworks, prompt injection protections, AI-specific incident response, and fine-grained agent permissions?

## Reliability
- What are the Recovery Time Objective (RTO) and Recovery Point Objective (RPO) targets, and does the architecture support them?
- Is multi-Availability-Zone or multi-Region deployment used appropriately?
- Are there automated failover and self-healing mechanisms?
- Is there a comprehensive backup and retention strategy?
- AI workloads: Are there resilient AI architectures with graceful degradation, model versioning, and agent failure recovery procedures?

## Performance Efficiency
- Are compute resources right-sized for the workload patterns?
- Are appropriate instance types selected (for example, accelerated compute for machine learning inference)?
- Is caching implemented where beneficial?
- AI workloads: Are inference acceleration techniques used (pruning, quantization)? Are vector stores optimized for financial data retrieval?
- Agentic AI: Are there efficient context management and parallel agent operation patterns?

## Cost Optimization
- Are Savings Plans or Reserved Instances applied to predictable workloads?
- Is there visibility into cost allocation by workload or team?
- Are serverless or consumption-based services used where appropriate?
- AI workloads: Are token costs tracked? Are model routing rules optimizing price-performance? Are cost-to-value metrics defined?
- Agentic AI: Are there strategies to minimize token consumption and optimize tool invocation costs?

## Sustainability
- Are lower-carbon Regions selected where feasible?
- Are resources scaled down during idle periods?
- Are managed Spot Instances or parameter-efficient fine-tuning (PEFT) techniques used for training?
- AI workloads: Are energy-efficient instances selected? Are sustainability key performance indicators defined for agent operations?

## Four FSI-Specific Design Principles
1. Documented Operational Planning: Three Lines of Defense model (operational managers, then risk and compliance functions, then internal audit).
2. Automated Infrastructure and Application Deployment: Infrastructure as Code, CI/CD, embedded security in the software development lifecycle.
3. Security by Design: pre-tested security templates, encryption by default, standardized configurations.
4. Automated Governance: account management automation, budget enforcement, security and compliance at scale.
