# Authorship Confidence Gate Reference

A two-axis scoring system applied to every writing sample before inclusion in voice analysis.

## Human Voice Axis (H1-H5)

| Score | Label | Meaning | Example |
|---|---|---|---|
| H5 | Pure native | Clearly written by the person with no AI assistance | Sent email drafted from scratch, meeting notes in their words |
| H4 | Lightly touched | Human-written with minor spell-check or grammar tool | Grammarly-edited email, autocorrect-touched message |
| H3 | Edited AI | AI-generated but substantially revised by the person | AI draft with 40%+ of content rewritten |
| H2 | Light edit AI | AI-generated with only surface edits | AI draft with minor tweaks (typo fixes, name insertion) |
| H1 | Pure AI | Entirely AI-generated, no meaningful human editing | Copy-pasted AI output sent without review |

## Confidence Axis (C1-C5)

| Score | Label | Meaning | Example |
|---|---|---|---|
| C1 | Certain | Clear evidence of authorship (sent mail, signed message) | Email in user's sent folder, message from their account |
| C2 | High | Strong attribution (personal folder, consistent style) | Doc in their personal drive, matches their known patterns |
| C3 | Likely | Reasonable attribution but some uncertainty | Shared doc with their edits, team channel they frequent |
| C4 | Uncertain | Could be ghostwritten, co-authored, or heavily edited | Exec comms, team announcements, formal documents |
| C5 | Unknown | No attribution evidence available | Unlabeled files, anonymous contributions |

## Inclusion Rules

Both axes must qualify. Apply these rules to determine how each sample is used:

| Human Voice Score | Confidence Score | Usage |
|---|---|---|
| H5/H4 | C1/C2 | Primary voice source: native writing. Full weight in analysis. |
| H3 | C1/C2/C3 | Editing fingerprint only: reveals what they change, not how they originate. |
| H2 | C1/C2/C3 | Output standard only: reveals what they accept as final, not their voice. |
| H1 | Any | Exclude entirely: AI writing, not human voice. |
| Any | C5 | Exclude entirely: no attribution evidence. |

## AI Contamination Threshold

If more than 40% of available samples score H2 or lower on the Human Voice axis (regardless of confidence axis), trigger the Native Voice Calibration Prompts procedure before proceeding to analysis.

## Native Voice Calibration Prompts

A standalone procedure triggered when AI contamination exceeds 40%. Purpose: generate clean H5-C1 material before voice analysis.

Procedure:

1. Inform the user: "Most of your available writing appears AI-assisted. I need a few samples of how YOU write without AI to build an accurate profile. This takes about 5 minutes."
2. Present 3-5 writing prompts (from the prompt bank in references/bootstrap-elicitation.md) one at a time.
3. Ask the user to respond without AI, in their natural voice. Fragments are fine.
4. Present 2-3 generic AI drafts (from the rewrite bank in references/bootstrap-elicitation.md) and ask the user to revise them.
5. Score all responses as H5-C1. These become the primary voice source.
6. Log the contamination trigger and native capture to the Governance Log.
7. Proceed to analysis with the native samples weighted as primary.
