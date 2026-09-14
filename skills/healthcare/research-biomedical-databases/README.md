---
description: "Human-facing overview, prerequisites, installation, and getting started for the Research Biomedical Databases skill."
last_updated: 2026-09-13
origin: original
---

# Research Biomedical Databases

Queries and chains biomedical databases (UniProt, ClinVar, gnomAD, Reactome, Open Targets, and more) to answer research questions.

## Overview

This skill orchestrates multi-database biomedical research by selecting the right tools and chaining them so output from one query feeds the next, across genomics, proteomics, pharmacology, and clinical data. It is for researchers doing variant interpretation, drug-target analysis, gene expression review, and protein analysis. It extends Amazon Quick by routing questions through the Biomni tool set exposed on an Amazon Bedrock AgentCore Gateway MCP server, with cited, cross-referenced answers.

## Pre-requisites

- biomni-research (custom/remote MCP server, runs on your own AWS account, required): an Amazon Bedrock AgentCore Gateway you deploy yourself and connect to Amazon Quick as an MCP server. It is not built into Amazon Quick or any other assistant. Without it connected, none of this skill's tools exist and no workflow can run.

## Installation

1. Deploy the `biomni-research` MCP server on your own AWS account first, following its deployment and connection guide (AWS prerequisites, deployment, authentication, and token refresh): https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/blob/main/mcp-servers/agentcore-gateway/biomni-research-tools/README.md
2. Connect the deployed server to Amazon Quick as a remotely hosted MCP server. The path depends on your surface:
   - Desktop app: Customize > Connectors, then Create > Cloud Connector (a remotely hosted MCP server is added as a cloud connector). See https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
   - Web console: Connectors > Create for your team > Model Context Protocol (MCP). See https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html
3. Verify the connection by asking the assistant to run `x_amz_bedrock_agentcore_search` with a query like "protein information"; it should return a ranked tool list.
4. Add this skill: https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Ask a biomedical database question such as "find protein info", "check variant pathogenicity", "find drug targets for a disease", or "look up pathways in Reactome". The skill routes your question to the right workflow and returns a cited answer.
