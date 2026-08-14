# Engram Schema Reference

The canonical engram object. The engram is a portable artifact: a structured file the user owns, plus a `portable_prompt` that can be pasted into any AI tool. Amazon Quick has no auto-load hook for a custom drafting runtime, so the engram is delivered as a file (YAML or JSON) at the user's chosen output location, not registered as a background model. Never persist the engram to memory, the knowledge graph, or any external endpoint. Every field is required unless marked optional.

```yaml
engram:
  metadata:
    display_name: string       # e.g. "Elizabeth MacMaster Voice"
    runtime_status: enum       # PROVISIONAL | EMERGING | DRAFT | PRODUCTION
    confidence_label: enum     # Provisional | Working | Strong | High
    build_path: enum           # fast_track | full_build | bootstrap | refresh
    sample_count: integer      # Total samples analyzed
    source_contexts: integer   # Number of distinct communication contexts
    created_at: ISO-8601       # First build timestamp
    updated_at: ISO-8601       # Most recent save timestamp
    refresh_trigger: string    # When to refresh (e.g. "30 days or 25 new samples")

  style_summary: string        # 200-500 word narrative: what makes this voice recognizable.
                               # Prefix with status tag: "[PRODUCTION - built from N samples]"
                               # or "[DRAFT - awaiting calibration]"
                               # or "[PROVISIONAL - bootstrap-built, N native samples]"

  registers: list              # 4-8 register objects
    - name: string             # e.g. "Executive leadership"
      use_for: string          # When to activate this register
      style_traits: string     # Tone, structure, rhythm for this register
      hard_limits: string      # What to never do in this register
      confidence: enum         # HIGH (5+ samples) | MEDIUM (3-4 samples) | LOW (1-2 samples)
      sample_ids: list[string] # Optional. References to source samples.

  vocabulary:
    signature_phrases: list[string]     # 10-20 phrases the user naturally uses
    anti_voice_markers: list[string]    # 10-20 phrases that signal "not them"
    fingerprint_sentences: list[string] # 10-15 full sentence patterns recognizably theirs

  rhythm:
    avg_sentence_length: float         # In words
    sentence_length_range: string      # e.g. "5-28 words, median 14"
    paragraph_shape: string            # e.g. "Short. 2-4 sentences. Topic sentence first."
    list_preference: string            # e.g. "Bullets for 3+ items, prose for fewer"
    punctuation_signature: string      # e.g. "Em dashes over parentheticals. No semicolons."

  hard_limits: list[string]            # 5-15 non-negotiable rules (formatting, tone, vocabulary)

  fidelity_rules:
    in_voice_when: list[string]        # 10 positive markers
    not_in_voice_when: list[string]    # 10 red flags
    validation_pairs: list             # 3-5 before/after test pairs
      - generic: string
        in_voice: string

  portable_prompt: string              # Under 500 words. Paste-able into any AI tool.
```

## Status Lifecycle

```
[No engram] -> PROVISIONAL -> EMERGING -> DRAFT -> PRODUCTION
                   ^                          ^
                   |                          |
             Bootstrap path            Fast Track / Full Build / Refresh
```

- PROVISIONAL: Bootstrap-built, awaiting real-work hardening
- EMERGING: First refresh with real samples completed (post-bootstrap only)
- DRAFT: Built from real samples, awaiting calibration pass
- PRODUCTION: Calibration passed, file written and verified

## Persistence and Verification

- Save: write the engram object to a file at the user's chosen output location, for example `[FirstName]_voice_engram.yaml`. Do not overwrite an existing engram file without explicit user instruction.
- Verify: read the engram file back after writing it and confirm the content matches. Log `ENGRAM_VERIFIED` on success or `ENGRAM_SAVE_FAILED` on mismatch.

## Worked Example

Below is an abbreviated example of the engram content written to file after a successful Fast Track build:

```yaml
metadata:
  display_name: "Sarah Chen Voice"
  runtime_status: "PRODUCTION"
  confidence_label: "Working"
  build_path: "fast_track"
  sample_count: 22
  source_contexts: 4
  created_at: "2026-07-17T14:30:00Z"
  updated_at: "2026-07-17T14:30:00Z"
  refresh_trigger: "Refresh after 30 days or 25 new samples"

style_summary: |
  [PRODUCTION - built from 22 samples across email, messaging, docs, and chat]
  Sarah writes like she manages: decisively, with zero tolerance for ambiguity
  about ownership. Her sentences are short (median 11 words). She opens with
  context ("Two things from yesterday's review:"), never with pleasantries.
  She uses numbered lists obsessively, even for two items. Escalations are
  always structured: what broke, why it matters, what she needs, by when.

registers:
  - name: "Leadership updates"
    use_for: "Weekly status to VP, org-wide announcements"
    style_traits: "Numbered structure. Evidence before claim. No filler."
    hard_limits: "Never open with 'I hope this finds you well.' Never hedge decisions."
    confidence: "HIGH"
  - name: "Direct reports"
    use_for: "1:1 follow-ups, feedback, delegation"
    style_traits: "Warm but direct. Short paragraphs. Always ends with clear next step."
    hard_limits: "No corporate-speak. No ambiguity on who owns what."
    confidence: "MEDIUM"
  - name: "Quick reply"
    use_for: "Chat, quick email responses"
    style_traits: "1-3 sentences. Lowercase ok. Emoji sparingly."
    hard_limits: "No formal closings. No 'just wanted to check in.'"
    confidence: "HIGH"

vocabulary:
  signature_phrases:
    - "Two things:"
    - "Net: [summary]"
    - "Blocking question:"
    - "To be direct,"
    - "What I need from you:"
  anti_voice_markers:
    - "I hope this message finds you well"
    - "Just wanted to circle back"
    - "Leverage our synergies"
    - "At the end of the day"
    - "Moving forward"
  fingerprint_sentences:
    - "I want to be direct about where we are."
    - "Two things from [context]:"
    - "Net: [one sentence summary]. Details below."

rhythm:
  avg_sentence_length: 11.3
  sentence_length_range: "4-24 words, median 11"
  paragraph_shape: "2-3 sentences. Topic sentence first. No transitions."
  list_preference: "Numbered lists for 2+ items. Always."
  punctuation_signature: "Em dashes over parentheticals. Period after list items. No semicolons."

hard_limits:
  - "Never open with pleasantries in internal email"
  - "Never use 'synergy', 'leverage', 'circle back', 'loop in'"
  - "Never hedge a decision that has been made"
  - "Never leave ownership ambiguous"
  - "No exclamation points in leadership communications"

fidelity_rules:
  in_voice_when:
    - "Opens with context or numbered structure"
    - "Sentences average under 15 words"
    - "Decisions are stated without hedging"
    - "Lists are numbered, not bulleted"
    - "Closes with a clear ask or next step"
  not_in_voice_when:
    - "Opens with 'I hope this finds you well'"
    - "Uses more than one adjective per noun"
    - "Paragraphs exceed 4 sentences"
    - "Contains 'just wanted to' or 'I think maybe'"
    - "Uses corporate buzzwords (synergy, leverage, align)"
  validation_pairs:
    - generic: "I wanted to reach out to align on next steps for the project."
      in_voice: "Two things on the project: 1. Timeline slipped to Friday. 2. I need your sign-off on scope by EOD Wednesday."

portable_prompt: |
  Write as Sarah Chen. Short sentences (median 11 words). Open with context
  or numbered structure, never pleasantries. Use "Net:" for summaries,
  "Two things:" for multi-point messages. Numbered lists always, even for
  two items. State decisions without hedging. End with a clear ask. Never
  use: synergy, leverage, circle back, loop in, I hope this finds you well.
  Em dashes over parentheses. No semicolons. No exclamation points to leaders.
```
