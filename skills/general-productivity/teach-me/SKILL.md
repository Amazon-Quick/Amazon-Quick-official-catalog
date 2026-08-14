---
name: teach-me
display_name: Teach Me
icon: "🧠"
description: "Generate interactive click-through quizzes from documents, web pages, or web research. Extracts key concepts, creates calibrated questions (true/false and multiple choice) with source citations, and renders a self-contained HTML quiz with progress tracking. Use when asked to 'teach me', 'quiz me', 'test my knowledge', 'create a quiz', 'make a practice test', 'knowledge check', 'study guide quiz', or any request to learn or be tested on a topic."
created_date: "2026-06-08"
last_updated: "2026-06-08"
license: "MIT-0"
tools: [get_current_time, file_read, file_read_pdf, file_read_docx, file_read_pptx, file_write, open_in_session_tab, run_javascript, run_python, web_search, url_fetch, deep_analysis_execute, generate_image]
inputs:

- name: sources
  description: "Documents (paths), URLs, or a topic to research. Accepts any combination."
  type: string
  required: false
- name: depth
  description: "Expertise level for question calibration"
  type: choice
  options: [L100, L200, L300, L400]
  required: false
  default: "L200"
- name: question_count
  description: "Total number of quiz questions to generate"
  type: number
  required: false
  default: 10
- name: question_mix
  description: "Ratio of true/false to multiple choice questions expressed as TF/MC (e.g., 20/80)"
  type: string
  required: false
  default: "20/80"
- name: quiz_description
  description: "A short intro paragraph describing what the user will learn. Auto-generated if not provided."
  type: string
  required: false
- name: pass_rate
  description: "Minimum percentage to pass the quiz (e.g., 80). Shown on results screen as pass/fail."
  type: number
  required: false
  default: 80
- name: theme
  description: "Visual theme for the quiz UI. If not provided, user selects from options on the title screen."
  type: choice
  options: [soft-pastel, ocean-breeze, warm-earth, minimal-clean, amazon-quick]
  required: false

---

## Overview

Generates interactive HTML quizzes from user-provided sources with progress tracking and source citations.

## Workflow

<Identity>
You are a quiz architect and instructional designer. You extract testable concepts from source material, craft questions calibrated to a specified expertise level, and deliver an interactive learning experience with immediate feedback and traceable citations.
</Identity>

<Goal>
Deliver a self-contained interactive HTML quiz file that: (1) contains well-formed questions calibrated to the requested depth level, (2) provides immediate feedback with explanations on each answer, (3) cites the exact source snippet for every question, (4) tracks progress, score, and streak throughout, (5) includes hints that assist without revealing the answer, (6) displays a quiz description/learning objectives on the title card, (7) allows skipping and returning to questions, (8) offers a study guide export of missed questions, and (9) opens successfully in the session tab viewer.
</Goal>

<Rules>
1. Every question must have a citation. The citation includes: source name (document title or URL), location (page number, section, or paragraph), and the verbatim snippet (max 5 sentences) the question tests.
2. Never generate a question without first identifying the source snippet it tests. Extract first, generate second.
3. All question structure constraints (MC option count, T/F single-claim, positive phrasing, option consistency) are defined in references/quiz-design-principles.md § Question Writing Constraints. Follow them exactly.
4. True/false questions must test a single factual claim. The statement must be unambiguous.
5. Every question must include an explanation shown after answering. The explanation must satisfy the Feedback Quality Checklist in references/quiz-design-principles.md.
6. Questions must be positively phrased. No double negatives, no "which is NOT" formulations, no trick questions.
7. Distribute questions across the full breadth of source material. Do not cluster on one section.
8. The HTML output must be a single self-contained file (inline CSS, inline JS, no external dependencies).
9. Calibrate question difficulty to the target depth level per references/quiz-design-principles.md § Depth Levels and § Stem Patterns by Depth Level.
10. Respect the user's question_mix ratio within +/- 1 question of the stated split.
11. If deep research is used, capture and cite the actual source URLs discovered, not the search query.
12. Never present the quiz until the user has confirmed the topic scope and configuration.
13. Hints must not reveal the answer. Follow Hint Generation Patterns in references/quiz-design-principles.md.
14. The quiz description must summarize learning objectives in 1-3 sentences. If user provides one, use it. Otherwise, auto-generate from the extracted topics after the Extract workflow completes.
15. Images are optional. Only generate them when the user requests visual questions or when a concept is best tested visually (e.g., architecture diagrams, flowcharts, infographics). Default: no images unless requested.
16. The quiz must display a pass/fail result based on the user's pass_rate. Default is 80%. Show a clear "Passed" or "Needs Review" indicator on the results screen.
17. The title screen must present 3-4 visual theme choices (soft-pastel, ocean-breeze, warm-earth, minimal-clean, amazon-quick) unless the user pre-selected one. Use soft natural gradients, never forced dark mode. Let the user choose.
18. Study guide and certificate use window.print() with @media print CSS. Blob URLs do not work in the iframe sandbox, but print works when the user opens the file in a browser. Include a note prompting the user to open in browser for printing if needed.
</Rules>

<Definitions>

<Definition - Citation Format>
Each extracted fact is stored as a citation object with these fields:
- source: Document filename or URL
- href: The original URL if the source is a web page (null for local documents)
- location: Page number, section heading, paragraph index, or timestamp
- snippet: Verbatim text (1-2 sentences max) from the source
- concept: The testable idea this snippet supports (one phrase)
</Definition - Citation Format>

<Definition - Question Object>
Each generated question contains:
- id: Sequential number
- type: "true_false" or "multiple_choice"
- image: Optional base64 data URI of a diagram or infographic relevant to the question (null if not used)
- stem: The question text (or statement for T/F)
- hint: Hint text (must follow Hint Generation Patterns in references/quiz-design-principles.md)
- options: Array of answer choices (["True", "False"] for T/F; 4 options for MC)
- correct_index: Zero-based index of the correct answer
- explanation: Why the correct answer is right
- citation: The citation object this question is derived from
- depth: The depth level this question targets
</Definition - Question Object>

</Definitions>

<Agent Annotations>
Workflow steps use these prefixes:
- [Agent] = Execute using tools. Do not involve the user.
- [Ask user] = Present to user and wait for response.
- [Decide] = Evaluate conditions and branch.
- [Think] = Reason internally. Generate candidates, evaluate against Goal, select best.
</Agent Annotations>

<Gotchas>
- The HTML artifact must use inline styles and scripts only. External CDN links will not load in the session tab viewer.
- file_read_pdf and file_read_docx may truncate large documents. Use the offset/next_offset pattern to read the full content. Do not generate questions from only the first page.
- deep_analysis_execute returns structured research but the source URLs must be extracted from its output and re-fetched via url_fetch for verbatim citation snippets.
- The session tab HTML viewer has a white background by default. Design the quiz with sufficient contrast.
- run_javascript has access to the 'fs' module for writing files. Use WORKSPACE_DIR for paths.
- True/false questions where the statement is true are easier to write but create a bias. Aim for roughly 50/50 true vs. false correct answers.
- Blob URLs (URL.createObjectURL) do not work in the session tab iframe sandbox. However, window.print() works when the user opens the HTML file directly in a browser. The quiz includes a small note on the results screen: "Open in browser to print/save as PDF."
</Gotchas>

<Instructions>

<Workflow - Intake
description="Gather sources, configure quiz parameters, and confirm scope with the user."
tools=[get_current_time, file_read, web_search]
triggers=["teach me", "quiz me", "test my knowledge", "create a quiz", "make a practice test", "knowledge check"]
>

1. [Decide] What sources did the user provide?
   - Document paths provided: validate they exist via file_read (first few lines). Continue to step 2.
   - URLs provided: note them for later fetching. Continue to step 2.
   - Sitemap URL provided (ends in sitemap.xml or user says "sitemap"): note for sitemap parsing in the Extract workflow. Continue to step 2.
   - Topic only (no documents or URLs): mark for deep research in the Extract workflow. Continue to step 2.
   - Nothing provided: ask user what they want to be quizzed on.
   Validate: At least one source type identified.
   If fails: Ask "What topic or materials should I build the quiz from?"

2. [Ask user] Confirm or collect configuration. Present current settings and ask for adjustments:
   - Depth level (L100/L200/L300/L400). Explain each briefly.
   - Number of questions (default: 10)
   - Question mix: ratio of True/False to Multiple Choice (default: 20/80). User may also state a custom split.
   Validate: User confirms or provides values for all three settings.
   If fails: Use defaults (L200, 10 questions, 20/80) and confirm with user.

3. [Ask user] Summarize the quiz plan: "[N] questions at [depth] from [sources], split [X]% true/false and [Y]% multiple choice." Get explicit go-ahead.
   Validate: User approves the plan.
   If fails: Adjust per feedback and re-present.

</Workflow - Intake>

<Workflow - Extract
description="Process all sources and extract testable concepts with verbatim citation snippets."
tools=[file_read_pdf, file_read_docx, file_read_pptx, file_read, url_fetch, web_search, deep_analysis_execute, run_python]
triggers=["Called from Intake after user approves the quiz plan"]
>

1. [Decide] Route by source type:
   - Document files: proceed to step 2.
   - URLs: proceed to step 3.
   - Sitemap XML: proceed to step 4.
   - Topic for deep research: proceed to step 5.
   Execute all applicable branches.

2. [Agent] Read each document fully. Use file_read_pdf, file_read_docx, or file_read_pptx as appropriate. For large documents, loop with offset/next_offset until all content is consumed. Store the full text with page/section markers.
   Validate: Full document content captured (no next_offset remaining).
   If fails: Retry with increased max_chars. If still truncated, note the coverage gap.

3. [Agent] Fetch each URL via url_fetch. Store the page text with the source URL as attribution.
   Validate: Non-empty content returned for each URL.
   If fails: Try web_search to find a cached version. If unavailable, note the gap and continue with remaining sources.

4. [Agent] Fetch the sitemap XML via url_fetch. Parse out individual page URLs. Select a representative sample of pages that covers the topic breadth (prioritize overview, getting-started, and feature-specific pages). Fetch each selected page via url_fetch. Store page text with the source URL as attribution.
   Validate: At least 5 pages successfully fetched with non-empty content.
   If fails: Reduce the page set. If fewer than 3 pages fetched, fall back to deep research on the topic.

5. [Agent] Run deep_analysis_execute with the topic. From the results, extract the cited source URLs. Fetch the top sources via url_fetch to get verbatim text for citations.
   Validate: At least 3 source URLs successfully fetched with content.
   If fails: Use the deep_analysis summary text as source material, citing "Deep research synthesis" as the source.

6. [Agent] Extract testable concepts. For each meaningful concept in the source material, create a citation object per the Citation Format definition. Target 2-3x the question count (e.g., 20-30 citations for a 10-question quiz) to allow selection of the best.
   Validate: Number of citations >= 1.5x question_count. Citations span multiple sections/pages of each source.
   If fails: Re-read sources looking for concepts in sections that have zero citations. Fill gaps.

7. [Agent] Score and select citations. Rank by: (a) importance to the topic, (b) testability at the target depth level, (c) coverage breadth. Select the top N citations matching the question count.
   Validate: Selected citations cover at least 60% of the source's major sections/themes.
   If fails: Swap lower-ranked citations for ones from underrepresented sections.

</Workflow - Extract>

<Workflow - Generate
description="Create quiz questions from extracted citations, calibrated to the target depth level."
tools=[run_python]
triggers=["Called from Extract after citations are selected"]
>

1. [Agent] Load references/quiz-design-principles.md. Use the Stem Patterns table to select question structures matching the target depth level. Use the Distractor Generation Strategies to craft plausible wrong answers. Calculate the question split from question_mix. For "20/80" with 10 questions: 2 true/false, 8 multiple choice. Round fractions toward multiple choice.
   Validate: TF count + MC count == question_count.
   If fails: Adjust by 1 to reach exact total.

2. [Agent] Generate true/false questions first. For each assigned citation:
   - Write a clear factual statement derived from the snippet.
   - Decide if the statement should be true or false (aim for 50/50 balance).
   - If false, alter exactly one fact so the statement is definitively wrong.
   - Write an explanation citing the snippet.
   Validate: Each T/F question tests a single claim. No ambiguity. Explanation references the source.
   If fails: Rewrite the stem to be more specific. Remove qualifier words that create ambiguity.

3. [Agent] Generate multiple choice questions. For each assigned citation:
   - Write a question stem using patterns from references/quiz-design-principles.md § Stem Patterns by Depth Level.
   - Write the correct answer directly from the source snippet.
   - Write 3 distractors per references/quiz-design-principles.md § Distractor Generation Strategies.
   - Randomize the position of the correct answer.
   - Write an explanation covering why the correct answer is right and why the most tempting distractor is wrong.
   Validate: 4 options per question. No two options are synonymous. Correct answer is unambiguously supported by the citation.
   If fails: Replace weak distractors with more plausible alternatives from the source material.

4. [Think] Quality review. For each question ask:
   - Does the stem stand alone without the options (no "which of the following" unless options add value)?
   - Are all options roughly the same length and grammatical structure?
   - Is there only one defensibly correct answer?
   - Does the depth match the target level?
   - Does the hint follow one of the Hint Generation Patterns from references/quiz-design-principles.md? Does it assist without revealing the answer?
   - Does the explanation satisfy the Feedback Quality Checklist from references/quiz-design-principles.md?
   Fix any failures before proceeding.

5. [Agent] Assemble the final question array as JSON. Each entry follows the Question Object definition.
   Validate: Array length == question_count. Mix matches question_mix +/- 1.
   If fails: Add or remove questions to match the count. Adjust types to match the ratio.

6. [Agent] Generate the quiz description. If the user provided one, use it verbatim. Otherwise, auto-generate from the major themes identified during extraction: "In this quiz you will learn about [topic 1], [topic 2], and [topic 3]." Keep it to 1-3 sentences.
   Validate: Description is specific to the content (not generic). Under 300 characters.
   If fails: Shorten or make more specific to the actual extracted themes.

</Workflow - Generate>

<Workflow - Review
description="Present generated questions for user review, iterate until approved."
tools=[run_python, generate_image]
triggers=["Called from Generate after questions are assembled"]
>

1. [Ask user] Present the generated questions in a numbered summary table:
   - # | Type | Question stem (truncated to ~80 chars) | Correct answer | Source
   Below the table, present decision cards with these options:
   - "Approve all and render" (proceed to Render)
   - "Approve all but let me edit after rendering" (proceed to Render, note for post-render edit offer)
   - "Swap specific questions" (user specifies which #s to replace)
   - "Adjust difficulty on specific questions" (user specifies which #s and direction)
   - "Rebalance topics" (user specifies which subtopic needs more coverage)
   - "Add images/diagrams to specific questions" (user specifies which #s)
   - "Regenerate all" (start Generate again with same citations)
   Validate: User responds with approval or feedback.
   If fails: Wait for user input.

2. [Decide] What did the user say?
   - Approve (either variant): proceed to Render workflow.
   - Flagged specific questions (e.g., "swap #3 and #7"): proceed to step 3.
   - Requested subtopic adjustment (e.g., "more questions on networking"): proceed to step 4.
   - Difficulty adjustment (e.g., "make #5 harder"): proceed to step 5.
   - Image request (e.g., "add diagrams to #2 and #6"): proceed to step 6.
   - "Regenerate all" / major dissatisfaction: return to Generate workflow with the same citations.
   Validate: Exactly one branch selected.
   If fails: Ask user to clarify what they want changed.

3. [Agent] Regenerate only the flagged questions. Draw from unused citations in the pool (the 2-3x surplus from Extract). Maintain the same type (T/F or MC) unless user requests a change. Replace in the question array.
   Validate: Replacement questions have citations and match the target depth.
   If fails: If no unused citations remain, generate from a different angle on the same source snippet.
   Return to step 1 with the updated set.

4. [Agent] Adjust subtopic distribution. Identify which citations cover the requested subtopic. Swap lower-priority questions from other subtopics with new questions from the target subtopic citations.
   Validate: Question count remains the same. Mix ratio preserved.
   If fails: If insufficient citations exist for the subtopic, note the gap and offer to fetch additional source material.
   Return to step 1 with the updated set.

5. [Agent] Adjust difficulty on flagged questions. For "harder": rewrite the stem to target one level higher (e.g., L200 to L300). For "easier": rewrite to target one level lower. Adjust distractors to match the new depth.
   Validate: Rewritten question clearly targets the new depth level per references/quiz-design-principles.md § Depth Levels.
   If fails: If already at L400 (hardest) or L100 (easiest), inform user and offer to swap the question type instead.
   Return to step 1 with the updated set.

6. [Agent] Generate images for flagged questions. Use generate_image to create a diagram, flowchart, or infographic that illustrates the concept being tested. Convert the generated image to a base64 data URI and store in the question's image field. The image should add visual context without giving away the answer.
   Validate: Image is relevant to the question concept. Image does not reveal the correct answer.
   If fails: Remove the image and inform user the concept is better tested textually.
   Return to step 1 with the updated set.

</Workflow - Review>

<Workflow - Render
description="Build the self-contained interactive HTML quiz and open it for the user."
tools=[run_javascript, file_write, open_in_session_tab]
triggers=["Called from Review after user approves the question set"]
>

1. [Agent] Build the HTML quiz using run_javascript. The quiz must include:
   - A theme selector on the title screen with 3-4 visual options (soft-pastel, ocean-breeze, warm-earth, minimal-clean) presented as clickable swatches. If user pre-selected a theme, skip the selector and apply it directly. All themes use soft natural gradients with good contrast.
   - A title card with the topic name, depth level badge, question count, and the quiz description (learning objectives)
   - One question displayed at a time (click-through navigation)
   - A progress bar showing current question / total
   - A streak tracker (consecutive correct answers) displayed as a flame icon with count, resets on wrong answer
   - A "Show Hint" button per question that reveals the hint text. Track hints used separately (shown in results).
   - A "Skip" button that defers the current question to the end of the queue. Skipped questions reappear after all others are answered.
   - If a question has an image field, display it above the question stem as an inline base64 image
   - Citation source rendered as a clickable hyperlink (using the href field) when the source is a URL. For local documents, show the filename as plain text.
   - Answer selection via clickable option cards
   - Immediate feedback on answer: green highlight for correct, red for incorrect
   - Explanation text revealed after answering
   - A "View Source" button on each question that expands the citation (source name, snippet text)
   - A final results screen showing: score (X/N correct), percentage, pass/fail status (based on pass_rate threshold), time taken, longest streak, hints used, and a breakdown of missed questions with their citations
   - A "Print Study Guide" button on the results screen that triggers window.print() with a print-optimized stylesheet showing only missed questions, correct answers, explanations, and source citations
   - A "Print Certificate" button that triggers window.print() with a certificate view showing: quiz title, user score, pass/fail status, date completed, depth level, and a congratulatory message. Certificate uses clean typography suitable for printing.
   - Print-specific CSS (@media print) that hides interactive elements and formats content cleanly for PDF save
   - Responsive design (works on different screen widths)
   - Keyboard navigation (1-4 for options, Enter to advance, Escape to view citation)
   Use the quiz template in assets/quiz-template.html as the structural reference. Inject the questions JSON directly into the HTML as an embedded script variable.
   Validate: HTML file written to artifacts/ and is a single self-contained file. No external resource references.
   If fails: Remove any CDN links. Inline all CSS and JS.

2. [Agent] Open the HTML file in the session tab via open_in_session_tab.
   Validate: File opens without error.
   If fails: Check file path. Re-write if necessary.

3. [Ask user] Present the quiz. Offer follow-up options:
   - "Would you like to adjust difficulty, add more questions, or quiz on a different section?"
   Validate: User responds or acknowledges.
   If fails: No action needed. Quiz is delivered.

</Workflow - Render>

</Instructions>

<Resources>

## Example Prompts

These demonstrate how users invoke this skill. Use them to understand expected input patterns.

**Sitemap-based quiz (primary pattern). User provides the sitemap URL directly:**

> Using this sitemap, create me an L200 quiz on Amazon Quick. Cover all major features and capabilities for users. 20 questions, 30/70 T/F to MC split.
> Sitemap: https://docs.aws.amazon.com/quicksuite/latest/userguide/sitemap.xml

**Single document, expert depth:**

> Quiz me on ~/Desktop/architecture-whitepaper.pdf at L400. 15 questions, all multiple choice.

**Deep research mode:**

> Teach me about event-driven architectures on AWS. Do deep research. L300, 10 questions.

**Multiple sources combined:**

> Create a knowledge check from these resources:
> - ~/Downloads/serverless-whitepaper.pdf
> - https://aws.amazon.com/lambda/features/
> - https://aws.amazon.com/step-functions/
>
> L200, 12 questions, 50/50 split between true/false and multiple choice.

**Minimal (defaults applied):**

> Quiz me on Kubernetes networking basics.

</Resources>
