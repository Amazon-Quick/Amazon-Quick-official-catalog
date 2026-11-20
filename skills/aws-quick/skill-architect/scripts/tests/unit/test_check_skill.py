"""
description: Unit tests for check_skill.py. Filesystem-free: each check is fed a SkillDocument built directly, so individual checks (checksum field, name format, tag balance, the Rules block and rule references, tools, headers, unused eval fixtures) are checked without reading a file.
last_updated: 2026-11-20

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime
import unittest

from check_skill import (
    SOURCES_PROBLEM,
    CheckStatus,
    EvalFiles,
    EvalFilesAudit,
    FileHeaderValidator,
    HeaderExtractor,
    SkillDocument,
    StalenessEvaluator,
    _RuleCrossRefCheck,
    _RuleFileCheck,
    _SkillChecksumFieldCheck,
    _TagBalanceCheck,
    _UnusedToolsCheck,
)
from run_rules import RULES_DIR, RuleId, RuleLoader

VALID_CHECKSUM = "sha256:" + "a" * 64


def _doc(frontmatter: str = "", body: str = "", dirname: str = "demo") -> SkillDocument:
    return SkillDocument(frontmatter=frontmatter, body=body, dirname=dirname)


RULES_BODY = (
    "<Definitions>\n- `<Rules>`: constraints.\n</Definitions>\n\n"
    "<Rules>\n1. Do x.\n2. Follow Rule {cited}.\n</Rules>\n"
)


class TestRulesBlock(unittest.TestCase):
    def test_block_starts_at_the_real_tag_not_a_backticked_mention(self) -> None:
        block = _doc(body=RULES_BODY.format(cited=1)).rules_block()
        self.assertTrue(block.startswith("\n1. Do x."))

    def test_inline_block_is_found(self) -> None:
        doc = _doc(body="<Rules>1. Keep every blocker.</Rules>\n")
        self.assertEqual(doc.rule_numbers(), [1])


class TestRuleCrossRefCheck(unittest.TestCase):
    def test_rule_citing_an_existing_rule_passes(self) -> None:
        result = _RuleCrossRefCheck().run(_doc(body=RULES_BODY.format(cited=1)))
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_rule_citing_a_missing_rule_fails(self) -> None:
        result = _RuleCrossRefCheck().run(_doc(body=RULES_BODY.format(cited=9)))
        self.assertIs(result.status_code, CheckStatus.FAIL)


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
    """The name format check now lives in references/rules/standard_rule.json;
    check_skill.py runs it through the rule engine with the same message."""

    def check(self) -> _RuleFileCheck:
        rules = {rule.id: rule for rule in RuleLoader(RULES_DIR).load()}
        return _RuleFileCheck(rules[RuleId.FRONTMATTER], "name_format")

    def test_valid_kebab_passes(self) -> None:
        result = self.check().run(_doc(frontmatter='name: "my-skill"'))
        self.assertIs(result.status_code, CheckStatus.PASS)
        self.assertEqual(result.status_reason, "name 'my-skill' is valid kebab-case")

    def test_uppercase_name_fails(self) -> None:
        result = self.check().run(_doc(frontmatter='name: "MySkill"'))
        self.assertIs(result.status_code, CheckStatus.FAIL)

    def test_missing_name_is_not_applicable(self) -> None:
        self.assertIsNone(self.check().run(_doc(frontmatter="description: x")))


class TestTagBalanceCheck(unittest.TestCase):
    def test_balanced_tags_pass(self) -> None:
        result = _TagBalanceCheck().run(_doc(body="<Rules>\n1. x\n</Rules>"))
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_unbalanced_tags_fail(self) -> None:
        result = _TagBalanceCheck().run(_doc(body="<Rules>\n1. x\n"))
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestUnusedToolsCheck(unittest.TestCase):
    _BODY = '<Workflow - Do\ndescription="x"\ntools=[file_read]\ntriggers=["x"]\n>'

    def test_every_declared_tool_used_passes(self) -> None:
        doc = _doc(frontmatter="tools: [file_read]", body=self._BODY)
        self.assertIs(_UnusedToolsCheck().run(doc).status_code, CheckStatus.PASS)

    def test_declared_tool_no_workflow_uses_warns(self) -> None:
        doc = _doc(frontmatter="tools: [file_read, web_search]", body=self._BODY)
        result = _UnusedToolsCheck().run(doc)
        self.assertIs(result.status_code, CheckStatus.WARNING)
        self.assertIn("web_search", result.status_reason)

    def test_no_declared_tools_is_not_applicable(self) -> None:
        self.assertIsNone(_UnusedToolsCheck().run(_doc(body=self._BODY)))


class TestFileHeaderValidator(unittest.TestCase):
    def test_header_without_sources_is_valid(self) -> None:
        text = '"""\ndescription: does x\nlast_updated: 2026-09-13\n"""\n'
        self.assertEqual(FileHeaderValidator(text, is_python=True).validate(), [])

    def test_sources_list_of_urls_is_valid(self) -> None:
        text = (
            '---\ndescription: "x"\nlast_updated: 2026-09-13\nsources:\n'
            "  - https://example.com/a\n  - https://example.com/b\n---\n# Title\n"
        )
        self.assertEqual(FileHeaderValidator(text, is_python=False).validate(), [])

    def test_inline_sources_list_is_valid(self) -> None:
        text = '---\ndescription: "x"\nlast_updated: 2026-09-13\nsources: [https://example.com]\n---\n'
        self.assertEqual(FileHeaderValidator(text, is_python=False).validate(), [])

    def test_source_that_is_not_a_url_fails(self) -> None:
        text = '---\ndescription: "x"\nlast_updated: 2026-09-13\nsources:\n  - the user guide\n---\n'
        self.assertEqual(
            FileHeaderValidator(text, is_python=False).validate(), [SOURCES_PROBLEM]
        )

    def test_empty_sources_fails(self) -> None:
        text = '---\ndescription: "x"\nlast_updated: 2026-09-13\nsources:\n---\n'
        self.assertEqual(
            FileHeaderValidator(text, is_python=False).validate(), [SOURCES_PROBLEM]
        )

    def test_missing_required_fields(self) -> None:
        missing = FileHeaderValidator(
            '"""just a docstring."""', is_python=True
        ).validate()
        self.assertEqual(set(missing), {"description", "last_updated"})


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


class TestEvalFilesAudit(unittest.TestCase):
    def audit(
        self, fixtures: list[str], references: str, summaries=()
    ) -> EvalFilesAudit:
        return EvalFilesAudit(
            EvalFiles(
                fixtures=fixtures, references=references, summaries=list(summaries)
            )
        )

    def test_fixture_named_by_a_case_is_used(self) -> None:
        refs = '"files": ["evals/files/a.md"]'
        self.assertEqual(self.audit(["a.md"], refs).unused(), [])

    def test_fixture_in_a_named_folder_is_used(self) -> None:
        refs = '"files": ["evals/files/demo-skill"]'
        self.assertEqual(self.audit(["demo-skill/SKILL.md"], refs).unused(), [])

    def test_fixture_nothing_names_is_unused(self) -> None:
        self.assertEqual(self.audit(["old.md"], '"files": []').unused(), ["old.md"])

    def test_only_the_latest_summary_is_kept(self) -> None:
        audit = self.audit(
            [], "", ["eval_result_2026-07-02.md", "eval_result_2026-11-19.md"]
        )
        self.assertEqual(audit.superseded(), ["eval_result_2026-07-02.md"])


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
