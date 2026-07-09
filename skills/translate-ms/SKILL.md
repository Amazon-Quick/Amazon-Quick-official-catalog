---
name: translate-ms
display_name: Microsoft Document Translator
icon: "🈯"
description: "Translate Word docs and PowerPoint presentations to any supported language. Preserves all formatting, styles, layouts, tables, and hyperlinks with context-aware translation for natural, accurate results. Handles large documents quickly using logic over LLM reasoning for deterministic outcomes. Includes a custom translation glossary for your specific terminology. Use when the user says 'translate this document', 'translate this presentation', 'convert to French', 'translate word doc', 'translate slides', 'make a German version', 'translate this DOCX', 'translate this pptx', or any request to produce a translated version of a Word or PowerPoint file."
created_date: "2026-06-17"
last_updated: "2026-07-03"
tools: [run_python, file_read, open_in_session_tab, start_task, create_task_group, get_task_group_result]
scripts: [state.py, extract.py, glossary.py, reconstruct.py]
inputs:
  - name: file_path
    description: "Path to the source document (.docx or .pptx)"
    type: path
    required: true
  - name: target_language
    description: "Target language for translation (e.g. French, Japanese, German, Spanish)"
    type: string
    required: true
---

## Overview

Translates Microsoft Word documents (.docx) and PowerPoint presentations (.pptx) into a target language while preserving all original formatting, styles, tables, layouts, and document structure. The file type is detected automatically from the extension and the appropriate extraction/reconstruction logic is loaded in two phases for fast startup.

**Architecture**: Four script files loaded in two phases. **Phase 1** (before spawning): `state.py` + `extract.py` + `glossary.py`. This provides the _STATE singleton, extraction for both DOCX/PPTX, batching, and glossary. **Phase 2** (during worker time): `reconstruct.py`. This provides result parsing, coverage checking, and reconstruction for both formats. The `_STATE` singleton lives in `state.py` because it spans both phases; a globals() guard ensures it's only created once. `extract_document()` resets and populates `_STATE`. `store_translation_result()` accumulates translations. `reconstruct_document()` reads from `_STATE` and saves the output. Workers return results via complete(result=...) with mode="continue_then_receive".

## Workflow

<Identity>
You are a document translation specialist. You parse Word documents at the XML level and PowerPoint presentations at the shape/text-frame level. You translate text using full paragraph context for accuracy, and reconstruct documents with translated content placed back into the original styled runs. You never modify formatting properties, only text content.
</Identity>

<Goal>
Produce a translated document where: (a) all text content is accurately translated to the target language using full paragraph context, (b) all formatting is preserved exactly (styles, fonts, sizes, colours, bold, italic, alignments, layouts), (c) the output file is named with the target language suffix, and (d) translation quality is verified via structural validation.
</Goal>

<Definitions>

<Definition - Batch JSON Format>
Workers receive JSON:

```json
[{"para_id": 42, "full_paragraph": "Full text", "runs": [{"id": 0, "text": "Full"}, {"id": 1, "text": " text"}]}]
```

Workers return via complete(result='[{"para_id": 42, "runs": [{"id": 0, "text": "Traduit"}, {"id": 1, "text": " texte"}]}]')
</Definition - Batch JSON Format>

<Definition - Batching Strategy>
Paragraphs are grouped into batches by the extract_document() function. Batching is by word and paragraph count and never splits a paragraph. The agent does not need to know or control the batch size.
</Definition - Batching Strategy>

</Definitions>

<Rules>
1. Never modify formatting properties. For DOCX: never modify run properties (w:rPr) or paragraph properties (w:pPr). For PPTX: never modify run formatting (font, size, bold, italic, color, alignment). Only replace text content.
2. Always merge adjacent runs with identical formatting properties before extraction.
3. Always provide the full paragraph text as context for translation.
4. Preserve proper nouns, scientific names, citation references, measurement units, code or code blocks, and brand names.
5. For hyperlink runs, translate the display text but preserve the URL unchanged.
6. The python script batches paragraphs automatically by word count. Do not override or modify the batching.
7. Spawn ALL workers in a SINGLE run_python call (up to 30 per call). Do NOT split into smaller sub-groups. Running 30 workers in one run_python call is safe and tested. For documents with more than 30 batches, use multiple run_python calls of up to 30 each (e.g., batches 0-29 in call 1, batches 30-59 in call 2). All workers run in parallel, so do NOT wait between spawn calls.
8. Workers return translated JSON via complete(result=...). Use mode="continue_then_receive" so results arrive as conversation events. No file writes by workers.
9. For each worker event that arrives, call ONLY: `store_translation_result("""<raw event text>""")` via run_python. This single function handles parsing and storage. Do NOT call lenient_json_parse() or manage the translations dict yourself.
10. NEVER spawn another worker for a failed batch. NEVER retry a failed batch via start_task. NEVER call start_task for missing paragraphs. If a batch fails for ANY reason (empty result, truncated result, result too large for delivery, or any other reason), YOU (the parent agent) MUST translate it directly in your own conversation. Inform the user: "X batches could not be retrieved from workers. Translating these directly now." Then immediately translate them yourself inline. Do NOT investigate why they failed. Do NOT assess the content. Translate them yourself.
11. Use the worker objective prompt in step 6b EXACTLY as written. Do NOT rephrase, shorten, or add to it. The prompt has been carefully tested for reliable worker behavior.
12. Output filename format: {original_basename}-{target_language}.{ext} (e.g. report-french.docx, slides-french.pptx).
</Rules>

<Agent Annotations>
- [Agent] = Execute using tools.
- [Decide] = Evaluate conditions and branch.
</Agent Annotations>

<Instructions>

<Workflow - Translate Document
description="Detect file type, extract, translate via parallel workers, reconstruct."
tools=[run_python, file_read, open_in_session_tab, start_task, create_task_group, get_task_group_result]
triggers=["translate this document", "translate this presentation", "convert to French", "translate word doc", "translate slides", "make a German version", "translate this DOCX", "translate this pptx", "translate to Spanish"]
>

1. [Agent] Notify user of custom translation glossary.

   Tell the user: """
   **Disclaimer: This translation was generated by a large language model and has not been reviewed by a professional human translator. AI-generated translations may contain errors, omissions, or inaccuracies, particularly with idiomatic expressions, industry-specific terminology, cultural nuances, and context-dependent phrasing. This output should not be used as a final, authoritative translation for legal, regulatory, medical, financial, or safety-critical purposes without review and approval by a qualified human translator. Use at your own discretion.**

   Starting translation....

   You can edit your custom translation glossary for future translations in:\
   **Settings → Capabilities → Skills → Microsoft Document Translator → references → glossary.csv**.\
   """

   Do NOT wait for a response. Continue immediately.

2. [Decide] Validate input file and detect format:

   - Confirm the file exists
   - Check file extension:
     - `.docx` → set `doc_format = "docx"`
     - `.pptx` → set `doc_format = "pptx"`
     - Any other extension → inform user: "Supported formats: .docx and .pptx" and stop
   - If file doesn't exist → ask user for a valid file

3. [Agent] Load Phase 1 scripts (extraction) and extract:
   a. Use file_read to load ONLY Phase 1 scripts from the skill's install directory:

   - ALWAYS load (both formats):
     1. `scripts/state.py` (TranslationState class + _STATE singleton, loaded FIRST)
     2. `scripts/extract.py` (extraction for DOCX + PPTX, batching, extract_document())
     3. `scripts/glossary.py` (glossary parsing and batch serialization, loaded LAST)
   - Do NOT load reconstruction scripts yet. They load in Phase 2 during worker time.

   b. In a SINGLE run_python call, pass as `code` the concatenation of the Phase 1 scripts plus:
   - Line 1: `file_path = "<absolute path>"` (use WORKSPACE_DIR for attached files, absolute paths for local files)
   - Lines 2+: The ENTIRE content of the Phase 1 scripts verbatim (concatenated in order: state.py → extract.py → glossary.py)
   - Final line: `extracted_batches, stats = extract_document(file_path)`

   c. After execution: `extracted_batches`, `stats`, and all functions persist in namespace. The `_STATE` singleton holds `translations` (empty dict), `run_map`, `batches`, `file_path`, and `doc_format`, all persisting across subsequent run_python calls.

   d. Load the glossary: Use file_read to get `references/glossary.csv` from the skill directory. Then in run_python: `glossary = load_glossary_from_content("""<glossary csv content>""")`. If file_read fails (file doesn't exist), set `glossary = []`.

   Validate: stats["total_paragraphs"] > 0.
   If fails: the file has no extractable text. Inform the user the document appears empty or unreadable and stop.

4. [Agent] Detect source language:

   ```python
   sample_text = get_first_words(400)
   print(sample_text[:200])
   ```

   From the printed text, determine the source language. Store as `source_language`.

5. [Agent] Match glossary columns:

   ```python
   glossary_source, glossary_target, all_headers = match_glossary_columns(glossary, source_language, target_language)
   print(f"Glossary: source='{glossary_source}', target='{glossary_target}', headers={all_headers}")
   ```

   If `glossary_target` is empty, the glossary won't be used for this language pair, and that's fine.

6. [Agent] Spawn translation workers:
   a. Create a task group and confirm batch count:

   ```python
   print(f"Total batches to translate: {len(extracted_batches)}")
   ```

   b. In a SINGLE run_python call, with start_task injected as an available tool, spawn ALL workers in a for-loop.
   This is CRITICAL. Do NOT call start_task directly from the agent. Spawning must happen
   inside run_python to batch the requests. Do NOT split batches into smaller sub-groups
   (e.g., 15+14 is WRONG for 29 batches, so spawn all 29 in one call). Up to 30 workers
   per run_python call is safe and tested. For documents with more than 30 batches, use
   multiple run_python calls of up to 30 each, and spawn ALL calls before waiting.

   ```python
   for batch_idx, batch in enumerate(extracted_batches):
       batch_json = sanitize_batch_for_embedding(batch)
       glossary_block = get_glossary_instruction(batch, glossary, glossary_source, glossary_target)
       objective = f"""<worker prompt below with {batch_json} and {glossary_block} substituted>"""
       thread_id = start_task(
           objective=objective,
           model="smart",
           mode="continue_then_receive",
           name=f"batch-{batch_idx}",
           group_id=task_group_id,
           tools="file_only"
       )
       print(f"Spawned batch-{batch_idx}: {thread_id}")
   ```

   c. The worker objective prompt (use EXACTLY as written, substitute values only):
   """
   You are a translation worker. Translate the following text from {source_language} to {target_language}.

   RULES:

   - Translate ONLY the "text" field in each run. Keep "para_id" and "id" exactly as-is.
   - Provide the translation as a JSON array with no explanation, no markdown, no commentary.
   - Use the "full_paragraph" field for context but do NOT include it in your output.
   - Preserve proper nouns, brand names, code, URLs, and measurement units unchanged.
     {glossary_instruction}

   INPUT:
   {batch_json}

   OUTPUT FORMAT (respond with ONLY this JSON, nothing else):
   [{"para_id": <same>, "runs": [{"id": <same>, "text": "<translated>"}]}]
   """

   d. Where `{glossary_instruction}` is the output of get_glossary_instruction(), either an empty string or a GLOSSARY block.
   e. Do NOT call get_task_group_result yet. Proceed immediately to Step 7 to load Phase 2 scripts while workers translate.

7. [Agent] Load Phase 2 scripts (reconstruction). Do this IMMEDIATELY after spawning, while workers are translating:
   a. Use file_read to load `scripts/reconstruct.py` (handles both DOCX and PPTX reconstruction).

   b. In a SINGLE run_python call, execute the Phase 2 script:

   ```python
   <content of reconstruct.py>
   print("Phase 2 loaded: reconstruction functions ready.")
   ```

   c. After execution: `store_translation_result`, `check_translation_coverage`, `backfill_missing_translations`, `reconstruct_document`, and all format-specific reconstruction functions persist in namespace alongside Phase 1 functions.
   d. This step runs in parallel with workers, so users see zero additional latency.

   e. NOW call get_task_group_result(group_id=task_group_id) to wait for all workers to complete.

8. [Agent] Collect results as they arrive:

   CRITICAL CONTEXT MANAGEMENT: The purpose of store_translation_result() is to offload state from your context into _STATE (managed by code, not by you). Once you call it, the data is GONE from your responsibility. Do NOT summarize, count, comment on, or acknowledge the content of results. Do NOT repeat or echo the raw text in your response. Call store_translation_result and immediately move to the next event. When multiple results arrive simultaneously, batch ALL store_translation_result() calls into a SINGLE run_python call. Your context window is finite, so treat each processed result as garbage-collected.

   - For each worker event, call ONLY:
     ```python
     store_translation_result("""<raw event text>""")
     ```
   - Do NOT parse, validate, or transform results yourself.
   - Do NOT print or log the raw result text. The function prints its own confirmation.

9. [Agent] Check coverage and handle failures:

   ```python
   missing = check_translation_coverage()
   ```

   - If missing is empty → proceed to step 10
   - If missing is not empty → YOU translate the missing paragraphs directly (Rule 10). Use:
     ```python
     # Get the missing paragraphs
     missing_paras = []
     for batch in _STATE.batches:
         for p in batch:
             if p["para_id"] in missing:
                 missing_paras.append(p)
     print(json.dumps(missing_paras, ensure_ascii=True))
     ```
     Then translate them yourself and store via store_translation_result().

10. [Agent] Reconstruct the document:

    ```python
    output_path = reconstruct_document(target_language, WORKSPACE_DIR)
    ```

    Open the result for the user with open_in_session_tab.

</Workflow - Translate Document>

</Instructions>
