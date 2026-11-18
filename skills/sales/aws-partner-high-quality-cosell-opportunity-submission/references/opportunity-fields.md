---
description: "Required, recommended, and scored opportunity fields, with character limits and exact picklist values that AWS Partner Central accepts."
last_updated: 2026-11-16
origin: original
---

# Opportunity fields

Ask the partner for the required fields below, and suggest the recommended fields. Everything else in the opportunity form is optional and can be skipped. A draft that breaks a limit or uses a value outside a picklist is rejected by AWS Partner Central, so every value must follow the rule shown. Copy picklist values exactly, including spaces and punctuation. Use the end customer's details, not the reseller's.

## Scored fields

These five fields feed the Opportunity Quality Score. Next Steps and AWS Products are not required to submit, but leaving them empty lowers the score, so always fill them.

| Field | Rule |
|-------|------|
| Customer Business Problem | 20 to 2,000 characters, including spaces |
| Next Steps | Up to 255 characters. At least one action is a customer meeting. |
| Partner Primary Need from AWS | Required when the partner wants AWS sales support. One or more values from the Partner Primary Need values table below. |
| Solution | Required. At least one partner solution or AWS Marketplace product, in Limited or Public status. |
| AWS Products | The AWS services the customer will adopt |

## Partner Primary Need from AWS values

The field accepts only these values. Any Co-Sell value makes Sales activities required.

| Value | Use when the partner needs |
|-------|----------------------------|
| Co-Sell - Architectural Validation | AWS to confirm the proposed architecture follows AWS best practices |
| Co-Sell - Business Presentation | An AWS seller to join a customer presentation |
| Co-Sell - Competitive Information | AWS competitive resources and positioning |
| Co-Sell - Pricing Assistance | An AWS seller's help where the customer receives a discount, such as an existing AWS commitment |
| Co-Sell - Technical Consultation | An AWS Solutions Architect to answer questions on the proposed solution |
| Co-Sell - Total Cost of Ownership Evaluation | Help comparing cost on AWS against on-premises or other hosting |
| Co-Sell - Support for Public Tender / RFx | AWS support on a public sector tender or RFx |
| Co-Sell - Deal Support | General seller support with no specific action (counts as generic) |

Co-Sell - Deal Support on its own, or an empty field, counts as generic. The ask belongs in this field, not in the Customer Business Problem.

## Customer details

AWS uses the website and address to match the opportunity to the right AWS account team.

| Field | Rule |
|-------|------|
| Company name | Up to 120 characters |
| Website | The customer's primary domain with its protocol, such as `https://example.com`, 4 to 255 characters. A bare domain (`example.com`) fails submission validation. Not required for national security opportunities. |
| Industry | One value: Aerospace, Agriculture, Automotive, Computers and Electronics, Consumer Goods, Education, Energy - Oil and Gas, Energy - Power and Utilities, Financial Services, Gaming, Government, Healthcare, Hospitality, Life Sciences, Manufacturing, Marketing and Advertising, Media and Entertainment, Mining, Non-Profit Organization, Professional Services, Real Estate and Construction, Retail, Software and Internet, Telecommunications, Transportation and Logistics, Travel, Wholesale and Distribution, Other. If Other, describe the industry in up to 255 characters. |
| Address | Street and city (up to 255 characters each), state or region, postal code (up to 20 characters), and two-letter country code such as US, GB, DE, IN, or BR. For US customers, state and postal code are required. |
| National security | Required only when Industry is Government. Yes only if the project involves classified national security information. |
| Customer contacts | Required before submitting. Add at least the champion named in the Customer Business Problem, and the approver when known: first name, last name, business title, email, and phone in E.164 format (such as +14155550100). Text fields up to 80 characters. |

## Project details

| Field | Rule |
|-------|------|
| Title | Up to 255 characters. Name the customer, the workload, and the delivery model. |
| Use case | One value from the picklist, copied exactly. Values that contain a slash have a space on each side: `Migration / Database Migration`, not `Migration/Database Migration` (the API rejects the version without spaces). Other values include AI Machine Learning and Analytics; Security & Compliance; Containers & Serverless; Database; SAP. Pick the closest specific value. |
| Delivery model | One or more: SaaS or PaaS, BYOL or AMI, Managed Services, Professional Services, Resell, Other |
| Opportunity type | Net New Business, Expansion, or Flat Renewal |
| Stage | Target stage: Qualified, Technical Validation, Business Validation, or Committed. Never Launched or Closed Lost. A new opportunity is always created at Prospect with review status Pending Submission, and Stage can be changed only after AWS approves the submission. Record the target stage in the output and set it after approval. |
| Sales activities | Required when Partner Primary Need from AWS is any Co-Sell value. One or more, such as Initialized discussions with customer, Customer has shown interest in solution, Conducted POC / Demo, In evaluation / planning stage, Agreed on solution to Business Problem, Completed Action Plan, Finalized Deployment Need, SOW Signed. Pick only activities the notes support; a planned POC is not Conducted POC / Demo. |
| Target close date | YYYY-MM-DD, in the future. The date AWS billing is expected to start. |
| Expected AWS monthly revenue | Amount and currency. Use the AWS Pricing Calculator; its share link also fills the AWS Products field. ISVs and other partners who price in total contract value (TCV) can enter the TCV and the contract duration (1 to 144 months) instead, and AWS Partner Central converts them to monthly revenue. |
| Marketing development funds | Required only when the opportunity came from an AWS marketing activity. Yes or No. |

## Recommended fields

These are optional, but each one helps AWS route and act on the opportunity. Suggest them to the partner; do not hold the submission if they are missing.

| Field | Why it helps | Rule |
|-------|--------------|------|
| Customer AWS account ID | Matches the opportunity to the customer's AWS account and account team faster | 12 digits |
| Partner contacts | These people receive AWS seller communication and agent guidance, so name the people who will act on it. Maps to the `OpportunityTeam` attribute in the Partner Central API. | Up to two in the console, or up to ten through the API or MCP (the `OpportunityTeam` array) |
| Competitor name | Surfaces the competitive signal named in the Customer Business Problem | One value from the picklist |

## Delivery model options

- SaaS or PaaS: the partner's AWS-based solution deployed as SaaS or PaaS in the partner's AWS environment
- BYOL or AMI: the partner's AWS-based solution deployed as BYOL or AMI in the customer's AWS environment
- Managed Services: ongoing management of the customer's AWS environment, such as operations, billing support, or cost optimization
- Professional Services: consulting, design, implementation, advisory, or transformation planning
- Resell: AWS account and billing management for the partner's customer
- Other: a delivery model not listed above
