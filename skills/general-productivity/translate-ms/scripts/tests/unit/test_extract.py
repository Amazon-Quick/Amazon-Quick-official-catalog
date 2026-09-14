"""
description: Unit test for the translate-ms extract module verifying paragraph batching honors word/paragraph limits and word sampling, with no filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

try:
    from extract import _ParagraphBatcher, _WordSampler

    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - only triggers if deps are missing
    _IMPORT_ERROR = exc


@unittest.skipIf(_IMPORT_ERROR is not None, f"extract import failed: {_IMPORT_ERROR}")
class ParagraphBatcherTest(unittest.TestCase):
    def test_batches_split_on_word_limit(self) -> None:
        batcher = _ParagraphBatcher(words_per_batch=3, max_paras_per_batch=10)
        paragraphs = [
            {"para_id": 0, "full_paragraph": "one two"},
            {"para_id": 1, "full_paragraph": "three four"},
            {"para_id": 2, "full_paragraph": "five"},
        ]

        batches = batcher.batch(paragraphs)

        self.assertEqual(len(batches), 2)
        self.assertEqual([p["para_id"] for p in batches[0]], [0])
        self.assertEqual([p["para_id"] for p in batches[1]], [1, 2])

    def test_word_sampler_returns_first_n_words(self) -> None:
        sampler = _WordSampler()
        batches = [[{"full_paragraph": "alpha beta gamma delta"}]]

        self.assertEqual(sampler.sample(batches, 2), "alpha beta")


if __name__ == "__main__":
    unittest.main()
