---
name: catalog-poc-test
display_name: Catalog POC Test
description: Test plugin for the salesforce-catalog-poc branch. One dummy skill plus a Salesforce connector slot.
author: Amazon Quick
version: 0.1.0
kind: solution

skills:
  - sales/catalog-poc-test-skill

categories:
  - Sales

connectors:
  - key: salesforce
    label: Your Salesforce
    description: The Salesforce org this test plugin connects to.
    types: [SALESFORCE_CRM]
    required: true
---

# Catalog POC Test

Test-only plugin. It installs the Catalog POC Test Skill and asks for one Salesforce
connector, so the alternate catalog branch, the plugin list and the connector binding
step can be checked end to end.
