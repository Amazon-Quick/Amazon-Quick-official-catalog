"""
description: Unit tests for check_skill.py. Filesystem-free: each check is fed a SkillDocument built directly, so individual checks (checksum field, name format, tag balance) are verified without reading a file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime
import unittest

from check_skill import (
    CheckStatus,
    ContentDigest,
    FileHeaderValidator,
    HeaderExtractor,
    SkillDocument,
    StalenessEvaluator,
    _NameFormatCheck,
    _SkillChecksumFieldCheck,
    _TagBalanceCheck,
)

VALID_CHECKSUM = "sha256:" + "a" * 64


def _doc(frontmatter: str = "", body: str = "", dirname: str = "demo") -> SkillDocument:
    return SkillDocument(frontmatter=frontmatter, body=body, dirname=dirname)


class TestSkillChecksumFieldCheck(unittest.TestCase):
    def test_valid_checksum_passes(self) -> None:
        result = _SkillChecksumFieldCheck().run(
            _doc(frontmatter=f'checksum: "{VALID_CHECKSUM}"')
        )
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_missing_checksum_fails(self) -> None:
        result = _SkillChecksumFieldCheck().run(_doc(frontmatter="name: demo"))
        self.assertIs(result.status_code, CheckStatus.FAIL)

    def test_malformed_checksum_fails(self) -> None:
        result = _SkillChecksumFieldCheck().run(
            _doc(frontmatter='checksum: "sha256:nope"')
        )
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestNameFormatCheck(unittest.TestCase):
    def test_valid_kebab_passes(self) -> None:
        result = _NameFormatCheck().run(_doc(frontmatter='name: "my-skill"'))
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_uppercase_name_fails(self) -> None:
        result = _NameFormatCheck().run(_doc(frontmatter='name: "MySkill"'))
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestTagBalanceCheck(unittest.TestCase):
    def test_balanced_tags_pass(self) -> None:
        result = _TagBalanceCheck().run(_doc(body="<Rules>\n1. x\n</Rules>"))
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_unbalanced_tags_fail(self) -> None:
        result = _TagBalanceCheck().run(_doc(body="<Rules>\n1. x\n"))
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestFileHeaderValidator(unittest.TestCase):
    def test_compliant_python_header(self) -> None:
        text = '"""\ndescription: does x\nlast_updated: 2026-09-13\norigin: original\n"""\n'
        self.assertEqual(FileHeaderValidator(text, is_python=True).validate(), [])

    def test_compliant_markdown_header(self) -> None:
        text = (
            '---\ndescription: "x"\nlast_updated: 2026-09-13\n'
            "source_url: https://example.com\n---\n# Title\n"
        )
        self.assertEqual(FileHeaderValidator(text, is_python=False).validate(), [])

    def test_missing_provenance(self) -> None:
        text = '"""\ndescription: x\nlast_updated: 2026-09-13\n"""\n'
        self.assertEqual(
            FileHeaderValidator(text, is_python=True).validate(),
            ["source_url or origin"],
        )

    def test_missing_all_fields(self) -> None:
        missing = FileHeaderValidator(
            '"""just a docstring."""', is_python=True
        ).validate()
        self.assertEqual(
            set(missing), {"description", "last_updated", "source_url or origin"}
        )


class TestSkillDocumentAccessors(unittest.TestCase):
    def test_last_updated_reads_frontmatter(self) -> None:
        doc = _doc(frontmatter='last_updated: "2026-09-13"')
        self.assertEqual(doc.last_updated(), "2026-09-13")

    def test_last_updated_absent_is_none(self) -> None:
        self.assertIsNone(_doc(frontmatter="name: demo").last_updated())

    def test_checksum_value_reads_frontmatter(self) -> None:
        doc = _doc(frontmatter=f'checksum: "{VALID_CHECKSUM}"')
        self.assertEqual(doc.checksum_value(), VALID_CHECKSUM)


class TestStalenessEvaluator(unittest.TestCase):
    def _evaluator(
        self, year: int = 2026, month: int = 9, day: int = 13, months: int = 6
    ) -> StalenessEvaluator:
        return StalenessEvaluator(datetime.date(year, month, day), months=months)

    def test_date_before_cutoff_is_stale(self) -> None:
        self.assertTrue(self._evaluator().is_stale("2026-03-12"))

    def test_date_exactly_on_cutoff_is_not_stale(self) -> None:
        self.assertFalse(self._evaluator().is_stale("2026-03-13"))

    def test_recent_date_is_not_stale(self) -> None:
        self.assertFalse(self._evaluator().is_stale("2026-09-13"))

    def test_month_rollover_across_year(self) -> None:
        evaluator = self._evaluator(month=1, day=15)  # cutoff 2025-07-15
        self.assertTrue(evaluator.is_stale("2025-07-14"))
        self.assertFalse(evaluator.is_stale("2025-07-15"))

    def test_day_clamps_to_short_target_month(self) -> None:
        evaluator = self._evaluator(month=8, day=31)  # cutoff 2026-02-28
        self.assertFalse(evaluator.is_stale("2026-02-28"))
        self.assertTrue(evaluator.is_stale("2026-02-27"))

    def test_unparseable_date_is_not_stale(self) -> None:
        self.assertFalse(self._evaluator().is_stale("not-a-date"))


class TestContentDigest(unittest.TestCase):
    def test_digest_is_order_independent(self) -> None:
        first = ContentDigest({"a.md": b"one", "b.md": b"two"}).compute()
        second = ContentDigest({"b.md": b"two", "a.md": b"one"}).compute()
        self.assertEqual(first, second)

    def test_digest_changes_with_content(self) -> None:
        base = ContentDigest({"a.md": b"one"}).compute()
        changed = ContentDigest({"a.md": b"two"}).compute()
        self.assertNotEqual(base, changed)

    def test_digest_has_sha256_prefix(self) -> None:
        self.assertTrue(ContentDigest({"a.md": b"one"}).compute().startswith("sha256:"))

    def test_digest_matches_create_checksum_owner(self) -> None:
        # Guards the deliberate duplication: the validator's self-contained digest
        # must stay byte-identical to create_checksum's, or audits false-fail.
        from create_checksum import ManifestDigest

        manifest = {"SKILL.md": b"body", "scripts/x.py": b"code"}
        self.assertEqual(
            ContentDigest(manifest).compute(), ManifestDigest(manifest).compute()
        )


class TestHeaderExtractor(unittest.TestCase):
    def test_extracts_python_docstring(self) -> None:
        text = '"""\ndescription: x\nlast_updated: 2026-09-13\n"""\ncode = 1\n'
        self.assertIn("last_updated: 2026-09-13", HeaderExtractor(text, True).extract())

    def test_extracts_markdown_frontmatter(self) -> None:
        text = "---\ndescription: x\nlast_updated: 2026-09-13\n---\n# Title\n"
        self.assertIn(
            "last_updated: 2026-09-13", HeaderExtractor(text, False).extract()
        )


if __name__ == "__main__":
    unittest.main()
