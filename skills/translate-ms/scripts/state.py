"""
Shared translation state singleton for the translate-ms skill.

This module defines the TranslationState class and the _STATE singleton instance
that persists across all run_python calls for the entire translation lifecycle.

_STATE is intentionally in its own file (not in extract.py or reconstruct.py)
because it belongs to neither phase — it spans the full lifecycle:
  Phase 1 populates it (extract_document fills batches, run_map, stats)
  Phase 2 reads from it (store_translation_result adds translations,
                          reconstruct_document reads everything)

SINGLETON GUARANTEE:
  When loaded via Python's import system, the module cache ensures _STATE is
  only constructed once — subsequent `from state import _STATE` calls return
  the same object. When loaded via script concatenation (run_python code paste),
  the `if "_STATE" not in globals()` guard at the bottom prevents re-creation.
  Either way, the singleton is safe.
"""


class TranslationState:
    """Singleton holding all translation workflow state.

    Attributes:
        doc_format: "docx" or "pptx" (set by extract_document)
        file_path: absolute path to the source document
        translations: dict of {para_id: [runs]} accumulated from workers
        run_map: dict of {para_id: {merged_run_map, run_count}} for reconstruction
        batches: list of batches (each batch is a list of paragraph dicts)
        stats: dict of extraction statistics (total_paragraphs, body, tables, etc.)
    """

    def __init__(self):
        self.reset(None, None)

    def reset(self, doc_format, file_path):
        """Clear all state for a new translation run."""
        self.doc_format = doc_format
        self.file_path = file_path
        self.translations = {}
        self.run_map = {}
        self.batches = []
        self.stats = {}
        self._batch_results_received = 0


# Singleton guard — prevents re-creation in Quick's script concatenation mode.
if "_STATE" not in globals():
    _STATE = TranslationState()
