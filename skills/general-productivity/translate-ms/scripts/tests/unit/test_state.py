"""
description: Unit test for the translate-ms state module verifying TranslationState.reset clears all workflow fields without any filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

try:
    from state import TranslationState

    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - only triggers if deps are missing
    _IMPORT_ERROR = exc


@unittest.skipIf(_IMPORT_ERROR is not None, f"state import failed: {_IMPORT_ERROR}")
class TranslationStateResetTest(unittest.TestCase):
    def test_reset_clears_all_state(self) -> None:
        state = TranslationState()
        state.translations[1] = [{"id": 0, "text": "x"}]
        state.run_map[1] = {"merged_run_map": {0: [0]}, "run_count": 1}
        state.batches = [[{"para_id": 1}]]
        state.stats = {"total_paragraphs": 1}
        state._batch_results_received = 5

        state.reset("docx", "example.docx")

        self.assertEqual(state.doc_format, "docx")
        self.assertEqual(state.file_path, "example.docx")
        self.assertEqual(state.translations, {})
        self.assertEqual(state.run_map, {})
        self.assertEqual(state.batches, [])
        self.assertEqual(state.stats, {})
        self.assertEqual(state._batch_results_received, 0)


if __name__ == "__main__":
    unittest.main()
