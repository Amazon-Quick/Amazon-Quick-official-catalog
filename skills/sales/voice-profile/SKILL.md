---
name: voice-profile
display_name: Voice Profile (Preview)
description: "Build a reusable voice profile from recent sent emails and Slack messages, scoped to what was asked: the full profile of greetings, sign-offs, length, structure, tone and recurring phrases, one trait, or referenced messages. Use during setup or when outreach drafts should sound more like the user; requires access to sent mail (Slack is optional)."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:0a56e822b5aac3353a15a5d5d6753558741c673392804365531532b700d345e0"
id: "9358037b-d3d9-45bc-b109-88d423a334ae"
---
<!-- global-rules-bootstrap -->

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **⛔ WIDGET OUTPUT ONLY after data assembly.** Once all queries return, immediately call `display_widget` — at most a single one-line render-wait notice before it, and no summaries, transitions, or narration. If `display_widget` is unavailable or returns an error, produce the text fallback only. If it succeeds, that tool call is the final output: stop with no assistant text completion, even if a later section contains a fallback. The exceptions above do not apply after success.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **One idea per sentence.** In all generated content, if a sentence needs re-reading, it is carrying too much: split it.
- **Don't repeat the visual.** When a visualization or widget renders, the text around it tells the user what to conclude from the data. Do not restate numbers they can already see.
- **Use plain language.** Choose terms any reader understands on first read, with no domain knowledge or cultural context required. Avoid jargon and colloquialisms, and make labels signal what follows. Test: would a reader unfamiliar with the idiom understand the term and know what content to expect? Use "No engagement", not "went dark" or "ghosted".
- **Reproduce Salesforce terminology exactly.** Use the field labels, object names, and stage values the data returns; do not paraphrase them. Spell out acronyms on first use unless the term is an industry framework (for example, MEDDIC).
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **While following this skill, don't call `discover` or `describe`, and don't call any API or endpoint not written here. This file already has every query and widget reference you need. (Outside this skill, they're available as normal.)** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->


# Rules:

- **Scope reading and output to the prompt, never a default full profile.** "Build my voice profile" shows the voice attributes, referenced messages and a text next step; "what's my usual sign-off?" gets the answer, no cards; "show me examples of how I write" shows only the referenced messages. Think in lego blocks: a broad ask shows every block that carries real signal; a specific ask shows only the block(s) it names; a direct question gets no blocks. Don't show something just because you analyzed it.
- **Read only what the question needs** and present only that. Every pattern, phrase and excerpt comes from the sent emails and Slack messages you read; never invent one.

# Voice Profile

Extract your real writing patterns from sent email → a pasteable Voice & Messaging profile (draft-outreach and inbox-sweep reuse it). No Salesforce. One-time setup.

## 0. Email available? (hard gate)

No email connected / can't read sent mail → exit gracefully, exactly:

```
To build your voice profile, I need access to your email sent folder. Please connect your email account and re-run this skill.
```

Do NOT attempt workarounds, ask clarifying questions, or invent a profile. Just stop.

## 1. Pull + clean

Search sent folder: last 60 messages to **external** recipients (not your own domain). Dedupe by thread (keep the opener over replies). Strip quoted/forwarded text, signature blocks (repeated trailing lines), calendar boilerplate.
Never count drafts, emails to yourself, or messages with no external recipient: they are not how you write to others.
**Slack (optional):** if a Slack tool is available, also pull your own recent messages (up to 60, same period): DMs and channel replies you sent. Skip bot, workflow and automated posts, pasted code or logs, and messages under 3 words. No Slack tool, or the search fails → continue with email only and say so in `answer`; never ask the user to connect Slack.
A narrow ask still needs enough mail to count from, so keep the same pull; it only skips the analysis and messages it does not show.

## 2. Analyze the cleaned set

A one-trait ask ("what's my usual sign-off?") analyzes only that trait; the full profile analyzes all of them.
Analyze email and Slack separately; when a trait differs by channel, report both ("Email: …; Slack: …"). Slack usually has no greeting, sign-off or signature: say so rather than skipping the trait.

- **Greeting** — top 3 openers + frequency ("Hi [Name]," 60% / …)
- **Sign-off** — top 3 closers + frequency
- **Length** — median words, openers vs replies
- **Structure** — bullets vs prose, paragraph count
- **Tone** — formality (contractions? exclamations? lowercase?), directness (questions vs statements), and emoji use (how many messages contain emoji, which ones recur, per channel)
- **Phrases you use** — recurring non-generic 3–5 word phrases
- **What you don't do** — notable absences (no "hope this finds you well", no emoji, etc.)

**Deterministic profile evidence:** Key the cleaned set by message and thread after deduplication. Compute first-touch and reply medians from cleaned authored-text word counts (with one message in a class, that message's count is the median). Normalize phrase candidates only for case, whitespace, punctuation, and recipient-name placeholders; do not merge semantic paraphrases. Include a phrase only when it contains 3–5 words and appears in at least two distinct included messages, and show its distinct-message count. If none qualifies, write `None established from <N> messages` under `Phrases I use`; never promote a one-message excerpt to a recurring habit. Detect and retain a repeated trailing signature value before stripping signatures from analyzed bodies, and always render `Signature block:` with that value or `None detected`.

## 3. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/voice-profile", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- **Quoted phrases use typographic quotes** (“Hi [Name],”), never straight double quotes: an unescaped `"` inside a value breaks the JSON and the call fails.
- When `display_widget` is available the widget is the output; produce the section 4 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Next step (broad ask only):** send `nextStep.text` as one plain line telling the user to paste the profile into their assistant instructions so drafts sound like them. Never say the profile is saved, stored, set as default or applied: nothing here saves it. Omit `lead` unless a bold lead is natural.
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case, including `referencedMessages` and `referencedMessagesNote`) and keep each `anchorExamples[].channel` exactly `Email` or `Messages` (never translated), and write every other free-text field (`title`, `answer`, `attribute`, `finding`, ...) in that language. Quote the user's own emails as written. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, badges, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. The user's own emoji in quoted excerpts and in tone findings (“🎉 👋 🙌”) are content you report, not presentation you add: keep them exactly as written, but never decorate labels, titles or values with emoji of your own. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **Every value comes from the cleaned set in step 2:** frequencies are counted, phrases occur in several emails, and every referenced-message excerpt is the user's own words from email or Slack (shortened with "…", never rewritten). Skip a trait you could not detect rather than guessing.
- **Too little mail:** fewer than 10 cleaned emails and Slack messages combined → still send `title`, `answer` (say how many you found and that the profile is tentative) and `sources`, plus only the traits you could count. No sent mail to external recipients → `answer` says there was nothing to learn from; no cards.
- **Scope reading and output to the prompt** (see the table below): answer what the user asked about, not a default full profile.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to analyze.**

| The prompt is… | Send |
|---|---|
| **Broad** ("build my voice profile", "learn my voice", setup) | `title` + `answer` + `voiceAttributes` + `anchorExamples` + text-only `nextStep` + `sources`. No `callout` (a callout is for a dated, actionable trigger and almost never applies here) |
| **Specific: one trait** ("what's my usual sign-off?", "how long are my emails?") | `title` + `answer` + `sources`. No cards, no tail |
| **Specific: several traits** ("how formal is my tone and how do I open?") | `title` + `answer` + **only** `voiceAttributes` with those rows + `sources` |
| **Specific: examples** ("show me examples of how I write") | `title` + `answer` + **only** `anchorExamples` + `sources` |

#### Worked examples (the `props` object only)

Names, counts and dates below are illustrative; every value comes from the sent emails and Slack messages you read.

**Broad — "Build my voice profile"** (both cards, text-only next step):

```json
{
  "title": "Your writing voice is warm, concise and question-led – built from 42 sent emails and 18 Slack messages.",
  "answer": "- I analyzed **42 emails to external contacts** and **18 Slack messages** you sent between Aug 2 and Oct 18.\n- Your voice is **casual and upbeat**: emails open with **“Hi [Name],”** and sign off **“Best, Haley”**; Slack drops both.\n- Emails run **~60 words**; Slack messages are **one or two lines**.",
  "voiceAttributes": [
    { "attribute": "Greeting", "finding": "Email: “Hi [Name],” in **26 of 42** (62%). Slack: usually none, sometimes “hey!”." },
    { "attribute": "Sign-off", "finding": "Email: “Best, Haley” in **31 of 42** (74%). Slack: no sign-off." },
    { "attribute": "Tone", "finding": "Warm, casual, upbeat. Slack runs looser – light emoji (🎉 👋 🙌) and “lmk”." },
    { "attribute": "What you don't do", "finding": "No “Hope this finds you well”, no “Dear”." }
  ],
  "anchorExamples": [
    { "channel": "Email", "kind": "Opener", "text": "Hi Priya,\nGreat meeting you at the offsite. Happy to set up some time next week – does Tuesday work on your end?\nBest,\nHaley" },
    { "channel": "Messages", "kind": "Teammate DM", "text": "oh nice, congrats on the close! 🎉 lmk if you want a hand with the renewal deck" }
  ],
  "nextStep": { "text": "Paste it into your assistant instructions so drafts sound like you." },
  "sources": [
    { "label": "Sent emails – 42 to external recipients, Aug 2 – Oct 18" },
    { "label": "Slack – 18 messages you sent, Aug 2 – Oct 18" }
  ]
}
```

**Specific — "What's my usual sign-off?"** (the answer only):

```json
{
  "title": "You almost always sign off “Best, Haley”.",
  "answer": "- **31 of 42** sent emails (74%) close with **“Best, Haley”**.\n- Quick replies use **“Thanks!”** instead.",
  "sources": [{ "label": "Sent emails – 42 to external recipients, Aug 2 – Oct 18" }]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (voiceAttributes, anchorExamples), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question about one trait (e.g. 'what's my usual sign-off?') usually gets no cards and no tail. Every value comes from the cleaned sent emails and Slack messages you read; never invent a pattern, phrase or excerpt. Format every value as a ready-to-display string.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line that already describes the voice and what it was built from (e.g. 'Your writing voice is warm, concise and question-led – built from 42 sent emails and 18 Slack messages.'). The counts are the cleaned emails and Slack messages you analyzed. Plain text, no markdown. Never the skill name or 'Voice Profile: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence: what you analyzed, the overall tone with the top greeting and sign-off, and the length/structure pattern. Put **bold** inline on the key values (counts, quoted openers, word ranges), never on a whole bullet. Do not restate every row of the cards below it. Answer ONLY what was asked (scope the bullets to the prompt); no headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "voiceAttributes": {
          "type": "string",
          "default": "VOICE & MESSAGING",
          "description": "Heading of the voice attributes card. English: 'VOICE & MESSAGING'."
        },
        "colAttribute": {
          "type": "string",
          "default": "Attribute",
          "description": "Header of the attribute column. English: 'Attribute'."
        },
        "colFinding": {
          "type": "string",
          "default": "What I found",
          "description": "Header of the finding column. English: 'What I found'."
        },
        "referencedMessages": {
          "type": "string",
          "default": "Referenced Messages",
          "description": "Heading of the referenced messages card (rendered upper case). English: 'Referenced Messages'."
        },
        "referencedMessagesNote": {
          "type": "string",
          "default": "These are the actual messages the profile was learned from, tagged by channel. Once you add this profile to your assistant instructions, new drafts can follow this voice on the right channel.",
          "description": "Muted note under the referenced messages heading. English: 'These are the actual messages the profile was learned from, tagged by channel. Once you add this profile to your assistant instructions, new drafts can follow this voice on the right channel.'"
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "voiceAttributes": {
      "type": "array",
      "description": "OPTIONAL card 'VOICE & MESSAGING'. Include when the prompt asks to build, show or explain the voice profile as a whole, or names two or more traits. One row per trait you found, in this order: Greeting, Sign-off, Length, Structure, Tone, Phrases you use, What you don't do, Signature block; skip a trait you could not detect. Omit the key otherwise; never send an empty array.",
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": [
          "attribute",
          "finding"
        ],
        "properties": {
          "attribute": {
            "type": "string",
            "description": "The trait name, plain text (e.g. 'Greeting', 'Sign-off', 'Phrases you use')."
          },
          "finding": {
            "type": "string",
            "description": "What you found for that trait, one or two sentences with frequencies where you counted them; when email and Slack differ, give both ('Email: …; Slack: …') (e.g. '“Hi [Name],” in **26 of 42** (62%); replies often open straight in.'). Put quoted phrases in typographic quotes (“ ”), never straight double quotes, so the JSON stays valid. Put **bold** on the key values only."
          }
        }
      }
    },
    "anchorExamples": {
      "type": "array",
      "description": "OPTIONAL card 'REFERENCED MESSAGES'. Include when building the full profile, or when the prompt asks for examples. 2-4 short excerpts from real cleaned sent emails and Slack messages that best show the voice: email messages first, then a Slack message. Quote the user's own words only, including any emoji they actually used (quoted and forwarded text, signatures and boilerplate stripped); shorten with '…', never rewrite. Omit the key otherwise; never send an empty array.",
      "maxItems": 4,
      "items": {
        "type": "object",
        "required": [
          "channel",
          "text"
        ],
        "properties": {
          "channel": {
            "type": "string",
            "enum": ["Email", "Messages"],
            "description": "Where the message was sent: exactly 'Email' or 'Messages' (Slack), always in English even when the reply is in another language. The renderer shows it as an upper-case channel badge with a channel icon and tone; do not add icons or emoji to it."
          },
          "kind": {
            "type": "string",
            "description": "OPTIONAL. What kind of message it is, shown as a second upper-case badge (e.g. 'Reply', 'Reply · celebratory', 'Teammate DM', 'Channel reply'). Omit if there is nothing useful to say."
          },
          "text": {
            "type": "string",
            "description": "The excerpt, with line breaks as '\\n'. Plain text, no markdown."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive: rarely applies to a voice profile. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if there is a dated trigger AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence: the trigger and the move in one sentence, ending with a period."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text after the bold lead: why it matters and what to do."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain text suggestion line with NO button. For a broad ask (the full profile) send it: a pointer such as 'Paste it into your assistant instructions so drafts sound like you'. Never claim the profile is saved, stored or applied. Use INSTEAD of callout, never both.",
      "required": [
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Optional bold lead (the suggested move). Omit to show the text alone."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences: the suggested move, ending with an offer to help if natural. Never say the profile is saved or applied."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. What the profile was learned from: one entry per channel read (sent mail, Slack), with the count and the time span it covers (e.g. 'Sent emails – 42 to external recipients, Aug 2 – Oct 18', 'Slack – 18 messages you sent, Aug 2 – Oct 18'). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Sent emails – 42 to external recipients, Aug 2 – Oct 18')."
          },
          "url": {
            "type": "string",
            "description": "Link to the source. Omit if none."
          }
        }
      }
    }
  }
}
```

## 4. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope it to the prompt as well: a one-trait ask gets a one- or two-line answer, not the template below.

```
# Voice Profile — built from <N> sent emails

## Voice & Messaging
**Greeting:** <top opener> (<N%>)
**Sign-off:** <top closer>
**Length:** ~<N> words first-touch, ~<N> replies
**Structure:** <prose / bullets / mixed>
**Tone:** <2–3 adjectives>
**Phrases I use:** "<phrase>" · "<phrase>"
**What I don't do:** <pattern> · <pattern>
**Signature block:** <detected signature>

## Anchor examples
**Opener:** > <excerpt from a real sent email>
**Reply:** > <excerpt>

Look right? If you'd like, paste this into your own AWS Quick instructions so draft-outreach and inbox-sweep can reuse your voice.
```
