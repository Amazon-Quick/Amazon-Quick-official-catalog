---
title: What are skills in Amazon Quick?
description: Learn how reusable skills teach Amazon Quick agents to follow task-specific instructions, use tools, and work with reference files.
---

# What are skills in Amazon Quick?

A skill is a set of instructions that tells Amazon Quick how to do a specific task, such as preparing your weekly status update from your team's template. You write the instructions once, and Amazon Quick follows them whenever that task comes up, instead of you explaining how you want it done in every conversation.

## How Amazon Quick finds a skill

Amazon Quick doesn't load every installed skill into each conversation. It reads only each skill's name and description, and when your request matches a description, or you ask for a skill by name, it loads that skill's full instructions and follows them. This keeps the skills you aren't using out of the conversation, and it means the description decides whether someone who doesn't know a skill's name ever gets it. [Write the description for someone who has never seen the skill](build-skills.md#write-the-description-for-someone-who-has-never-seen-the-skill) covers how to write one that matches the way people ask.

## What's in a skill

A skill is a folder with a file named `SKILL.md` at its root. The file starts with a block of settings between two `---` lines, called the **frontmatter**, which holds the skill's name and description along with settings such as the inputs it asks for and the tools it uses. The following frontmatter is from Template Enforcer, a skill in the catalog that applies a brand guide or style template to a document, shortened to its first two inputs:

```yaml
---
name: template-enforcer
display_name: Template Enforcer
description: "Apply a brand guide or style template to any document, presentation, or generated output, enforcing colors, fonts, tone of voice, logo placement, and formatting rules. Use when the user says 'apply brand guide', 'enforce template', 'match this style', 'make it consistent with our brand', 'apply our formatting', 'style this document', or any request to align a document with a visual/brand standard."
created_date: "2026-06-15"
last_updated: "2026-09-13"
tools: [file_read, file_read_pdf, file_read_docx, file_read_pptx, run_python, file_write, open_in_session_tab]
inputs:
  - name: source_document
    description: "Path to the document or content to be styled"
    type: path
    required: true
  - name: brand_guide
    description: "Path to brand guide document (PDF, DOCX, or XLSX) or previously saved brand profile name"
    type: string
    required: true
---
```

Below the frontmatter are the steps Amazon Quick follows when the skill is active, and the folder can also hold the scripts, templates, and reference files those steps use. A skill doesn't include the connectors or other dependencies it relies on, such as Outlook or Slack, so many skills also include a `README.md` that lists what you need to set up before you run them.

To learn about the other kinds of skills in Amazon Quick, including the system skills that come with it, see [Skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html) in the Amazon Quick User Guide.
