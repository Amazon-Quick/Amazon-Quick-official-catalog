---
description: "How demo.json is read and changed through scripts/run_demo_store.py, the change-set format, the build call, and how to handle a user's hand edits."
last_updated: 2026-10-27
origin: original
---

# Demo Store

<purpose>
demo.json, in the work folder, holds everything needed to rebuild the demo. The agent changes it by writing a change set and applying it with scripts/run_demo_store.py, and the user may also edit it by hand (see the hand-edits section). An apply is all or nothing. If any part of a change is invalid, demo.json stays as it was and the error names the field.
</purpose>

<calls>
In run_python, the skill's scripts import by module name.

```python
import run_demo_store, create_demo

run_demo_store.main(
    ["--store", "<work>/demo.json", "apply", "--changes", "<work>/changes.json"]
)
run_demo_store.main(["--store", "<work>/demo.json", "show"])
run_demo_store.main(
    ["--store", "<work>/demo.json", "export", "--out", "<work>/snapshot.json"]
)
create_demo.main(
    [
        "--snapshot",
        "<work>/snapshot.json",
        "--template",
        "<skill>/assets/demo-template.html",
        "--out-dir",
        "<work>",
    ]
)
```

Each call returns 0 on success and logs one line per result. The first apply creates demo.json. `show` prints one line per step with its chapter, hotspot, load time, media count, and blur count, which is what you need to resume or edit.

For a smaller file, add `--max-width` with a width in pixels to the create_demo call. Screenshots wider than that are shrunk in index.html, while the files on disk keep their full resolution. Half the captured width keeps a quarter of the pixels.
</calls>

<change_set>
Every key is optional, except that the first change set must create the demo with `demo.title` and `demo.start_url`.

```json
{
  "demo": {
    "title": "Exploring the experiment catalog",
    "start_url": "https://example.com/explore",
    "goal": "Find an experiment and read its details",
    "intro_title": "Find any experiment in under a minute",
    "intro_body": "See how to narrow thousands of studies to one and open its record.",
    "outro_title": "That's the whole path",
    "outro_body": "Use the same filters to find any study.",
    "cta_label": "Open the catalog",
    "cta_url": "https://example.com/explore",
    "accent": "#7c3aed"
  },
  "chapters": [{"position": 1, "title": "Find experiments"}, {"position": 2, "title": "Read a record"}],
  "steps": [
    {
      "position": 1,
      "chapter": 1,
      "title": "Every experiment in one table",
      "caption": "The explore page lists each experiment with its investigator and research area.",
      "action": "Filter by mission",
      "url": "https://example.com/explore",
      "screenshot": "screenshots/step-01.png",
      "load_ms": 5307,
      "hotspot": {"x": 1.2, "y": 61.0, "w": 14.5, "h": 2.6, "zoom": 1},
      "media": [{"kind": "video_file", "src": "media/overview.mp4", "caption": "Two-minute overview"}],
      "blurs": [{"x": 92.0, "y": 1.0, "w": 6.0, "h": 4.0, "reason": "avatar"}]
    }
  ],
  "load_events": [{"step": 1, "ready": true, "waited_ms": 4800, "detail": "table rows appeared"}],
  "delete_steps_from": null
}
```
</change_set>

<fields>
| Key | Behavior |
| --- | --- |
| `demo` | Only the fields given change. Intro and closing cards appear only when their titles are set. An `accent` that is not a `#rrggbb` color falls back to purple, and a `cta_url` that does not start with http or https leaves the button out. |
| `chapters` | Added or updated by `position`. Steps refer to a chapter by its position. |
| `steps` | Added or updated by `position`. A new step needs `title`, `caption`, `url`, and `screenshot` (a path relative to demo.json). Later changes can send only the fields that change. |
| `hotspot` | Viewport percentages from <Resource key="measure-hotspot">, with `zoom` from 1 to 3. Send `"clear_hotspot": true` to remove one. Every step except the last needs a hotspot before a build. |
| `media` | Replaces the step's media. A `video_link` is a direct https .mp4 or .webm link and plays only online. A `video_file` is an .mp4 or .webm file relative to demo.json, embedded in full so it plays offline. An `image` is a .png, .jpg, .gif, .webp, or .svg file relative to demo.json, or an https image link. |
| `blurs` | Replaces the step's blur areas. The build destroys those pixels in index.html, and the screenshot on disk stays sharp. |
| `load_events` | Appended to the `load_log` list in demo.json, for reviewing slow pages later. |
| `delete_steps_from` | Removes that step and every later one, clears the action on the new last step, and removes any chapter left with no steps. |
</fields>

<hand_edits>
A user can open demo.json in any text editor, change it, save it, and ask for a rebuild. demo.json stores the whole demo rather than a change, so its shape differs from a change set. `demo` holds the demo fields, `chapters` and `steps` are complete lists, and each step keeps its `hotspot`, `media`, and `blurs` inline.

```json
{
  "version": 1,
  "demo": {"title": "Exploring the experiment catalog", "start_url": "https://example.com/explore", "goal": "", "intro_title": null, "intro_body": null, "outro_title": null, "outro_body": null, "cta_label": null, "cta_url": null, "accent": "#7c3aed", "created_at": "2026-10-27T15:00:00+00:00", "updated_at": "2026-10-27T15:00:00+00:00"},
  "chapters": [{"position": 1, "title": "Find experiments"}],
  "steps": [
    {"position": 1, "chapter": 1, "title": "Every experiment in one table", "caption": "The explore page lists each experiment.", "action": "Open the first row", "url": "https://example.com/explore", "screenshot": "screenshots/step-01.png", "load_ms": 5307, "hotspot": {"x": 1.2, "y": 61.0, "w": 14.5, "h": 2.6, "zoom": 1.0}, "media": [], "blurs": [{"x": 92.0, "y": 1.0, "w": 6.0, "h": 4.0, "reason": "avatar"}], "captured_at": "2026-10-27T15:00:00+00:00"}
  ],
  "load_log": []
}
```

Users can safely change any title, caption, or action, the intro, closing, and call-to-action fields, chapter titles, a step's `chapter`, hotspot and blur numbers, `zoom`, and `media` items. Removing whole steps from the end also works, as long as the new last step's `action` is cleared. The build leaves out any chapter that has no steps. Leave `version`, `created_at`, `captured_at`, and `load_log` as they are when fixing a hand edit.

The rebuild rejects the mistakes below. Explain each one to the user in plain words.

| Mistake | What to tell the user |
| --- | --- |
| Broken JSON, such as a missing comma, quote, or bracket | The line the error gives and what is missing there |
| A misspelled or unknown field name | The name, and the field it was probably meant to be. Unknown fields are rejected so a typo is never silently ignored. |
| A hotspot or blur area outside 0 to 100, or running past an edge (`x + w` or `y + h` over 100) | The step and the numbers |
| `zoom` outside 1 to 3, a missing hotspot before the last step, a gap in step positions, or a chapter that does not exist | The step |
| A `screenshot` or media path with no file next to demo.json | The path |

A bad `accent` or `cta_url` does not stop the build, as the fields table explains. Mention it when it happens.
</hand_edits>
