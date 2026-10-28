"""
description: Unit tests for run_demo_store.py. Filesystem-free: every test starts from an in-memory DemoStore and applies injected change sets, so upserts, media and blur replacement, trimming, all-or-nothing applies, hand edits, and build validation are verified without a demo file.
last_updated: 2026-10-27
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from pydantic import ValidationError
from run_demo_store import (
    ChangeApplier,
    ChangeSet,
    DemoStore,
    DemoStoreError,
    Hotspot,
    SnapshotReader,
    SummaryFormatter,
)

NOW = "2026-10-27T15:00:00+00:00"
LATER = "2026-10-27T16:00:00+00:00"
SPOT = {"x": 10, "y": 10, "w": 5, "h": 4}


def _step(position: int, hotspot: dict | None = None) -> dict:
    step = {
        "position": position,
        "title": f"Screen {position}",
        "caption": "What is on screen.",
        "url": "https://example.com",
        "screenshot": f"screenshots/step-{position:02d}.png",
    }
    if hotspot is not None:
        step["hotspot"] = hotspot
    return step


def _apply(store: DemoStore, changes: dict, now: str = NOW) -> DemoStore:
    return ChangeApplier(store, ChangeSet.model_validate(changes), now).apply()


def _seeded() -> DemoStore:
    return _apply(
        DemoStore(),
        {
            "demo": {"title": "Tour", "start_url": "https://example.com"},
            "chapters": [{"position": 1, "title": "Find it"}],
            "steps": [dict(_step(1, SPOT), chapter=1), _step(2, SPOT), _step(3)],
        },
    )


class TestChangeApplier(unittest.TestCase):
    def test_first_change_set_must_create_the_demo(self) -> None:
        with self.assertRaises(DemoStoreError):
            _apply(DemoStore(), {"steps": [_step(1)]})

    def test_new_step_needs_its_required_fields(self) -> None:
        with self.assertRaises(DemoStoreError):
            _apply(_seeded(), {"steps": [{"position": 4, "title": "Only a title"}]})

    def test_failed_apply_leaves_the_store_unchanged(self) -> None:
        store = _seeded()
        before = store.model_dump()
        with self.assertRaises(DemoStoreError):
            _apply(
                store,
                {
                    "steps": [
                        {"position": 2, "caption": "Changed."},
                        {"position": 9, "title": "Bad"},
                    ]
                },
            )
        self.assertEqual(store.model_dump(), before)

    def test_partial_update_keeps_other_fields(self) -> None:
        store = _apply(
            _seeded(), {"steps": [{"position": 2, "caption": "New caption."}]}
        )
        step = SnapshotReader(store).read().steps[1]
        self.assertEqual(step.caption, "New caption.")
        self.assertEqual(step.title, "Screen 2")
        self.assertIsNotNone(step.hotspot)

    def test_media_and_blurs_are_replaced_not_appended(self) -> None:
        media = [{"kind": "video_link", "src": "https://example.com/clip.mp4"}]
        store = _apply(
            _seeded(),
            {"steps": [{"position": 1, "media": media, "blurs": [SPOT, SPOT]}]},
        )
        store = _apply(
            store, {"steps": [{"position": 1, "media": media, "blurs": [SPOT]}]}
        )
        step = SnapshotReader(store).read().steps[0]
        self.assertEqual(len(step.media), 1)
        self.assertEqual(len(step.blurs), 1)

    def test_clear_hotspot_removes_it(self) -> None:
        store = _apply(_seeded(), {"steps": [{"position": 3, "hotspot": SPOT}]})
        store = _apply(store, {"steps": [{"position": 3, "clear_hotspot": True}]})
        self.assertIsNone(store.steps[2].hotspot)

    def test_trimming_clears_the_new_last_action(self) -> None:
        store = _apply(
            _seeded(),
            {
                "steps": [{"position": 2, "action": "Click Next"}],
                "delete_steps_from": 3,
            },
        )
        snapshot = SnapshotReader(store).read()
        self.assertEqual(len(snapshot.steps), 2)
        self.assertEqual(snapshot.steps[-1].action, "")

    def test_trimming_removes_a_chapter_left_with_no_steps(self) -> None:
        store = _apply(
            _seeded(),
            {
                "chapters": [{"position": 2, "title": "Read it"}],
                "steps": [{"position": 3, "chapter": 2}],
            },
        )
        store = _apply(store, {"delete_steps_from": 3})
        self.assertEqual([chapter.title for chapter in store.chapters], ["Find it"])

    def test_updated_at_moves_and_created_at_stays(self) -> None:
        store = _apply(_seeded(), {"demo": {"goal": "Find it fast"}}, now=LATER)
        self.assertEqual(store.demo.created_at, NOW)
        self.assertEqual(store.demo.updated_at, LATER)
        self.assertEqual(store.demo.goal, "Find it fast")

    def test_load_events_are_appended(self) -> None:
        event = {"step": 1, "ready": True, "waited_ms": 1200, "detail": "rows appeared"}
        store = _apply(_seeded(), {"load_events": [event]})
        store = _apply(store, {"load_events": [event]})
        self.assertEqual(len(store.load_log), 2)
        self.assertEqual(store.load_log[0].logged_at, NOW)

    def test_store_round_trips_through_json(self) -> None:
        store = _seeded()
        self.assertEqual(DemoStore.model_validate_json(store.model_dump_json()), store)


class TestSnapshotReader(unittest.TestCase):
    def test_empty_store_cannot_be_built(self) -> None:
        with self.assertRaises(DemoStoreError):
            SnapshotReader(DemoStore()).read()

    def test_chapter_with_no_steps_is_left_out_of_the_build(self) -> None:
        raw = _seeded().model_dump()
        raw["chapters"].append({"position": 2, "title": "Read it"})
        snapshot = SnapshotReader(DemoStore.model_validate(raw)).read()
        self.assertEqual([chapter.title for chapter in snapshot.chapters], ["Find it"])

    def test_missing_hotspot_before_last_step_blocks_the_build(self) -> None:
        store = _apply(
            DemoStore(),
            {
                "demo": {"title": "Tour", "start_url": "https://example.com"},
                "steps": [_step(1), _step(2)],
            },
        )
        with self.assertRaises(DemoStoreError):
            SnapshotReader(store).read()

    def test_gap_in_positions_blocks_the_build(self) -> None:
        store = _apply(
            DemoStore(),
            {
                "demo": {"title": "Tour", "start_url": "https://example.com"},
                "steps": [_step(1, SPOT), _step(3)],
            },
        )
        with self.assertRaises(DemoStoreError):
            SnapshotReader(store).read()

    def test_summary_has_one_line_per_step(self) -> None:
        lines = SummaryFormatter(SnapshotReader(_seeded()).read()).render()
        self.assertEqual(len(lines), 4)
        self.assertIn("[Find it]", lines[1])


class TestHandEdits(unittest.TestCase):
    def test_valid_hand_edit_is_read(self) -> None:
        raw = _seeded().model_dump()
        raw["steps"][0]["caption"] = "Edited by hand."
        store = DemoStore.model_validate(raw)
        self.assertEqual(
            SnapshotReader(store).read().steps[0].caption, "Edited by hand."
        )

    def test_misspelled_field_is_rejected(self) -> None:
        raw = _seeded().model_dump()
        raw["steps"][0]["captoin"] = "Typo."
        with self.assertRaises(ValidationError):
            DemoStore.model_validate(raw)

    def test_hotspot_moved_past_the_edge_is_rejected(self) -> None:
        raw = _seeded().model_dump()
        raw["steps"][0]["hotspot"]["x"] = 98
        with self.assertRaises(ValidationError):
            DemoStore.model_validate(raw)

    def test_broken_json_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            DemoStore.model_validate_json(_seeded().model_dump_json()[:-5])


class TestRectValidation(unittest.TestCase):
    def test_hotspot_past_the_edge_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Hotspot(x=95, y=10, w=10, h=5)

    def test_zoom_above_the_limit_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Hotspot(x=10, y=10, w=5, h=5, zoom=4)


if __name__ == "__main__":
    unittest.main()
