"""
description: Unit test for the translate-ms reconstruct module verifying word-boundary splitting and injected-parser result storage, with no filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

try:
    from reconstruct import _TextSplitter, _TranslationResultStore
    from state import _STATE

    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - only triggers if deps are missing
    _IMPORT_ERROR = exc


class _FakeParser:
    """Test double that returns a fixed parse result regardless of input."""

    def __init__(self, result: object) -> None:
        self._result = result

    def parse(self, raw_text: str) -> object:
        return self._result


@unittest.skipIf(
    _IMPORT_ERROR is not None, f"reconstruct import failed: {_IMPORT_ERROR}"
)
class ReconstructLogicTest(unittest.TestCase):
    def test_text_splitter_splits_on_word_boundaries(self) -> None:
        splitter = _TextSplitter()

        parts = splitter.split("one two three four", 2)

        self.assertEqual(parts, ["one two ", "three four"])

    def test_store_records_translations_via_injected_parser(self) -> None:
        _STATE.reset("docx", "example.docx")
        fake = _FakeParser([{"para_id": 7, "runs": [{"id": 0, "text": "hola"}]}])
        store = _TranslationResultStore(fake)

        store.store("ignored raw text")

        self.assertEqual(_STATE.translations[7], [{"id": 0, "text": "hola"}])


if __name__ == "__main__":
    unittest.main()
