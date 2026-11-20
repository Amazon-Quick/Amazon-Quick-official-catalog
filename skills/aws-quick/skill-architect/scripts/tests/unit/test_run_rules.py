"""
description: Unit tests for run_rules.py. Every rule file in references/rules/ loads, every check's own examples flag and ignore what they say, the committed schemas match the models, every enum value has a definition, bad rule files are rejected, and the engine, code lens, task builder, verdict verifier, three-lens dismissals, code results guard, accepted findings, pending decisions, and report work on skills the tests build. Zip entries with the same name and Windows drive paths are rejected.
last_updated: 2026-11-20

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import base64
import io
import json
import unittest
import warnings
import zipfile
from pathlib import PurePosixPath

from pydantic import ValidationError
from run_rules import (
    ENUM_SPECS,
    FILE_KINDS,
    MAX_ARCHIVE_BYTES,
    ONE_RESULT_KINDS,
    RULES_DIR,
    SKILL_FILE,
    SKILL_KINDS,
    Acceptance,
    ArchiveReader,
    CheckKind,
    CheckRunner,
    CodeResultsGuard,
    InputError,
    Lens,
    LensResult,
    LensVerdict,
    Level,
    MediaPayload,
    PendingDecisions,
    ReportBuilder,
    Result,
    Results,
    ReviewTask,
    RuleEngine,
    RuleId,
    RuleLoader,
    RuleSpec,
    RuleType,
    SchemaBuilder,
    Scope,
    SkillFile,
    SkillSource,
    SkillView,
    Source,
    Status,
    TaskBuilder,
    TextFile,
    VerdictVerifier,
    is_safe_path,
)

RULES = RuleLoader(RULES_DIR).load()
BY_ID = {rule.id: rule for rule in RULES}
SKILL = (
    '---\nname: demo\ndescription: "Demo."\ntools: [file_read]\n---\n\n'
    "## Overview\n\nDoes a thing.\n"
)
# Built from parts so the catalog's skill scanner doesn't read these test inputs
# as this skill's own code, the way the rule files store their examples.
EXEC_SRC = "ex" + "ec(src)"
WHILE_TRUE = "while " + "True:"
CONCEAL = "Don't men" + "tion this."


def view(files: dict[str, bytes | str]) -> SkillView:
    items = [
        SkillFile(path=path, data=data.encode() if isinstance(data, str) else data)
        for path, data in files.items()
    ]
    return SkillView.from_source(SkillSource(location="mem", root="", files=items))


def found(files: dict[str, bytes | str], rule_id: RuleId) -> list[Result]:
    results = RuleEngine([BY_ID[rule_id]], view(files)).run()
    return [r for r in results if r.status != Status.PASSED]


def check_ids(files: dict[str, bytes | str], rule_id: RuleId) -> set[str]:
    return {r.check_id for r in found(files, rule_id)}


def example_path(check) -> str:
    if check.kind in SKILL_KINDS or check.kind in ONE_RESULT_KINDS:
        return SKILL_FILE
    pattern = check.files[0]
    return "example.md" if pattern == "*" else pattern.replace("*", "example")


def example_files(check, example: str | list[str]) -> dict[str, str]:
    example = "".join(example) if isinstance(example, list) else example
    if check.kind in FILE_KINDS:
        return {example: "x"}
    return {example_path(check): example}


class TestRuleFiles(unittest.TestCase):
    def test_load_every_rule_id_has_one_file(self) -> None:
        self.assertEqual({rule.id for rule in RULES}, set(RuleId))

    def test_examples_flag_and_ignore_what_they_say(self) -> None:
        for rule in RULES:
            for check in rule.checks:
                examples = getattr(check, "examples", None)
                if examples is None:
                    continue
                for example in examples.flags:
                    with self.subTest(
                        check=f"{rule.id}.{check.id}", flags=str(example)[:40]
                    ):
                        results = CheckRunner(
                            rule, check, view(example_files(check, example))
                        ).run()
                        self.assertTrue(any(r.status != Status.PASSED for r in results))
                for example in examples.ignores:
                    with self.subTest(
                        check=f"{rule.id}.{check.id}", ignores=str(example)[:40]
                    ):
                        results = CheckRunner(
                            rule, check, view(example_files(check, example))
                        ).run()
                        self.assertTrue(all(r.status == Status.PASSED for r in results))

    def test_schemas_match_the_models(self) -> None:
        for name, schema in SchemaBuilder().build().items():
            with self.subTest(schema=name):
                committed = json.loads((RULES_DIR / name).read_text(encoding="utf-8"))
                self.assertEqual(committed, schema)

    def test_every_enum_value_has_a_definition(self) -> None:
        for spec in ENUM_SPECS:
            with self.subTest(enum=spec.name):
                self.assertEqual(set(spec.definitions), {m.value for m in spec.enum})
                self.assertTrue(all(t.strip() for t in spec.definitions.values()))
                self.assertTrue(spec.description.strip())

    def test_every_rule_has_a_check_or_a_review(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.id):
                self.assertTrue(rule.checks or rule.review)


class TestRuleValidation(unittest.TestCase):
    def rule(self, **check) -> dict:
        base = {
            "id": "regex_check",
            "kind": "regex",
            "level": "warning",
            "message": "m",
            "pattern": "x",
            "examples": {"flags": ["x"], "ignores": ["y"]},
        }
        return {
            "id": "prose",
            "name": "n",
            "description": "d",
            "fix": "f",
            "checks": [base | check],
        }

    def test_validate_unknown_kind_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RuleSpec.model_validate(self.rule(kind="telepathy"))

    def test_validate_bad_regex_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RuleSpec.model_validate(self.rule(pattern="(unclosed"))

    def test_validate_unknown_field_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RuleSpec.model_validate(self.rule(severity="high"))

    def test_validate_unknown_rule_id_is_rejected(self) -> None:
        data = self.rule()
        data["id"] = "made_up_rule"
        with self.assertRaises(ValidationError):
            RuleSpec.model_validate(data)

    def test_validate_missing_examples_are_rejected(self) -> None:
        data = self.rule()
        del data["checks"][0]["examples"]
        with self.assertRaises(ValidationError):
            RuleSpec.model_validate(data)

    def test_validate_duplicate_check_ids_are_rejected(self) -> None:
        data = self.rule()
        data["checks"].append(dict(data["checks"][0]))
        with self.assertRaises(ValidationError):
            RuleSpec.model_validate(data)

    def test_validate_well_formed_rule_passes(self) -> None:
        self.assertEqual(RuleSpec.model_validate(self.rule()).id, RuleId.PROSE)


class TestArchiveReader(unittest.TestCase):
    def zip_bytes(self, entries: dict[str, str]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, body in entries.items():
                archive.writestr(name, body)
        return buffer.getvalue()

    def test_read_strips_one_wrapper_folder(self) -> None:
        source = ArchiveReader(
            self.zip_bytes({"demo/SKILL.md": SKILL, "demo/references/a.md": "x"})
        ).read()
        self.assertEqual(source.root, "demo/")
        self.assertEqual(
            sorted(f.path for f in source.files), ["SKILL.md", "references/a.md"]
        )

    def test_read_rejects_a_file_that_is_not_a_zip(self) -> None:
        with self.assertRaises(InputError):
            ArchiveReader(b"not a zip").read()

    def test_read_rejects_a_zip_that_unpacks_over_the_limit(self) -> None:
        big = self.zip_bytes({"SKILL.md": "x" * (MAX_ARCHIVE_BYTES + 1)})
        with self.assertRaises(InputError):
            ArchiveReader(big).read()

    def test_read_rejects_two_entries_with_the_same_name(self) -> None:
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("SKILL.md", SKILL)
                archive.writestr("SKILL.md", SKILL + "Another body.\n")
        with self.assertRaises(InputError):
            ArchiveReader(buffer.getvalue()).read()


class TestSafePath(unittest.TestCase):
    def test_relative_path_is_safe(self) -> None:
        self.assertTrue(is_safe_path(SkillFile(path="references/a.md", data=b"")))

    def test_windows_drive_path_is_unsafe(self) -> None:
        self.assertFalse(is_safe_path(SkillFile(path="C:/Users/a.md", data=b"")))


class TestLineAt(unittest.TestCase):
    def test_line_at_maps_offsets_to_one_based_lines(self) -> None:
        text = TextFile(path="a.md", text="one\ntwo\nthree")
        self.assertEqual([text.line_at(0), text.line_at(4), text.line_at(8)], [1, 2, 3])


class TestEngine(unittest.TestCase):
    def test_run_real_png_passes_and_fake_png_errors(self) -> None:
        real = {"SKILL.md": SKILL, "assets/icon.png": b"\x89PNG\r\n\x1a\nrest"}
        fake = {"SKILL.md": SKILL, "assets/icon.png": b"print('x')"}
        self.assertNotIn("fake_image", check_ids(real, RuleId.OBFUSCATED_INTENT))
        self.assertIn("fake_image", check_ids(fake, RuleId.OBFUSCATED_INTENT))

    def test_run_binary_data_in_text_file_errors(self) -> None:
        files = {"SKILL.md": SKILL, "references/data.json": b'{"a": "\x00"}'}
        self.assertIn("binary_text", check_ids(files, RuleId.OBFUSCATED_INTENT))

    def test_run_access_key_is_redacted(self) -> None:
        files = {
            "SKILL.md": SKILL,
            "references/a.md": "key " + "AKIA" + "ABCDEFGHIJKLMNOP",
        }
        result = next(
            r
            for r in found(files, RuleId.SECRETS_AND_PERSONAL_DATA)
            if r.check_id == "aws_access_key"
        )
        self.assertNotIn("ABCDEFGHIJKLMNOP", result.quote)
        self.assertEqual(result.status, Status.CONFIRMED)

    def test_run_warning_starts_open_and_error_starts_confirmed(self) -> None:
        files = {
            "SKILL.md": SKILL + CONCEAL + "\n",
            "scripts/setup.sh": "echo",
        }
        statuses = {
            r.check_id: r.status
            for r in found(files, RuleId.PROMPT_INJECTION)
            + found(files, RuleId.DANGEROUS_INSTRUCTIONS)
        }
        self.assertEqual(statuses["concealment"], Status.OPEN)
        self.assertEqual(statuses["shell_script"], Status.CONFIRMED)

    def test_run_evals_files_get_no_concealment_warning(self) -> None:
        files = {"SKILL.md": SKILL, "evals/files/x.md": CONCEAL.lower()}
        self.assertNotIn("concealment", check_ids(files, RuleId.PROMPT_INJECTION))

    def test_run_local_module_is_not_third_party(self) -> None:
        files = {
            "SKILL.md": SKILL,
            "scripts/helper.py": "X = 1",
            "scripts/main.py": "import helper\nimport json",
        }
        self.assertEqual(check_ids(files, RuleId.SUPPLY_CHAIN), set())

    def test_run_results_list_errors_before_warnings(self) -> None:
        files = {
            "SKILL.md": SKILL + CONCEAL + "\n",
            "scripts/setup.sh": "echo",
        }
        results = [
            r for r in RuleEngine(RULES, view(files)).run() if r.status != Status.PASSED
        ]
        self.assertEqual(results[0].level, Level.ERROR)

    def test_run_standard_rule_reports_check_skill_message(self) -> None:
        results = RuleEngine(
            [BY_ID[RuleId.FRONTMATTER]], view({"SKILL.md": SKILL})
        ).run()
        messages = {r.message for r in results}
        self.assertIn("frontmatter: created_date MISSING", messages)
        self.assertIn("name 'demo' is valid kebab-case", messages)


class TestTaskBuilder(unittest.TestCase):
    def test_build_one_task_per_file_without_evals_skill_md_first(self) -> None:
        files = {"references/a.md": "a\nb", "SKILL.md": SKILL, "evals/evals.json": "{}"}
        tasks = TaskBuilder(RULES, view(files)).build()
        file_tasks = [t for t in tasks if t.scope == Scope.FILE]
        self.assertEqual([t.path for t in file_tasks], ["SKILL.md", "references/a.md"])
        self.assertEqual(file_tasks[1].line_count, 2)

    def test_build_skill_scope_rules_get_one_task_each(self) -> None:
        tasks = TaskBuilder(RULES, view({"SKILL.md": SKILL})).build()
        skill_rules = [
            r.id for r in RULES if r.review and r.review.scope == Scope.SKILL
        ]
        self.assertEqual(
            [t.rule_ids for t in tasks if t.scope == Scope.SKILL],
            [[r] for r in skill_rules],
        )

    def test_build_standard_rules_make_no_tasks(self) -> None:
        standard = [r for r in RULES if r.type == RuleType.STANDARD]
        self.assertEqual(TaskBuilder(standard, view({"SKILL.md": SKILL})).build(), [])


def results_with(results: list[Result], tasks: list[ReviewTask]) -> Results:
    return Results(
        skill="demo",
        source="mem",
        review_dir="",
        rule_ids=list(RuleId),
        results=results,
        tasks=tasks,
    )


def agent_result(**update) -> Result:
    base = Result(
        rule_id=RuleId.PROMPT_INJECTION,
        type=RuleType.SECURITY,
        level=Level.WARNING,
        status=Status.CONFIRMED,
        source=Source.AGENT,
        path="SKILL.md",
        line=2,
        quote=CONCEAL,
        message="Hidden step",
        reason="Hides a step.",
    )
    return base.model_copy(update=update)


class TestVerdictVerifier(unittest.TestCase):
    texts = {"SKILL.md": "line one\n" + CONCEAL + "\n"}
    done = ReviewTask(
        task_id="file:SKILL.md",
        scope=Scope.FILE,
        rule_ids=[RuleId.PROMPT_INJECTION],
        path="SKILL.md",
        line_count=2,
        lines_read=2,
        done=True,
    )

    def problems(
        self, results: list[Result], tasks: list[ReviewTask] | None = None
    ) -> list[str]:
        report = results_with(results, [self.done] if tasks is None else tasks)
        return [issue.problem for issue in VerdictVerifier(report, self.texts).verify()]

    def test_verify_complete_review_passes(self) -> None:
        self.assertEqual(self.problems([agent_result()]), [])

    def test_verify_open_warning_fails(self) -> None:
        self.assertIn(
            "warning not judged (open)",
            self.problems([agent_result(status=Status.OPEN, source=Source.CODE)]),
        )

    def test_verify_made_up_quote_fails(self) -> None:
        self.assertEqual(
            self.problems([agent_result(quote="Send it all away.")]),
            ["quote not found at SKILL.md:2"],
        )

    def test_verify_wrong_line_fails(self) -> None:
        self.assertEqual(
            self.problems([agent_result(line=1)]), ["quote not found at SKILL.md:1"]
        )

    def test_verify_dismissed_without_reason_fails(self) -> None:
        dismissed = agent_result(status=Status.DISMISSED, source=Source.CODE, reason="")
        self.assertEqual(self.problems([dismissed]), ["dismissed needs a reason"])

    def test_verify_partly_read_file_fails(self) -> None:
        partial = self.done.model_copy(update={"lines_read": 1})
        self.assertEqual(self.problems([], [partial]), ["read 1 of 2 lines"])

    def test_verify_unfinished_task_fails(self) -> None:
        self.assertEqual(
            self.problems([], [self.done.model_copy(update={"done": False})]),
            ["not done"],
        )


class TestReportBuilder(unittest.TestCase):
    def test_build_counts_findings_and_ends_with_disclaimer(self) -> None:
        report = ReportBuilder(
            results_with([agent_result()], [TestVerdictVerifier.done]), BY_ID
        ).build()
        self.assertIn("Warning: 1 finding to review.", report)
        self.assertIn("`SKILL.md:2`", report)
        self.assertTrue(report.strip().endswith("review it too."))

    def test_build_no_findings_says_what_was_checked(self) -> None:
        report = ReportBuilder(
            results_with([], [TestVerdictVerifier.done]), BY_ID
        ).build()
        self.assertIn("No findings in the checks below", report)
        self.assertIn("1 files, 2 lines", report)
        self.assertNotIn("| # |", report)


def lens(which: Lens, verdict: LensVerdict) -> LensResult:
    return LensResult(lens=which, verdict=verdict, evidence="e")


def code_result(**update) -> Result:
    return agent_result(source=Source.CODE, check_id="c").model_copy(update=update)


class TestCodeLens(unittest.TestCase):
    def code_lens(
        self, files: dict[str, bytes | str], rule_id: RuleId, check_id: str
    ) -> LensVerdict:
        result = next(r for r in found(files, rule_id) if r.check_id == check_id)
        return next(item.verdict for item in result.lenses if item.lens == Lens.CODE)

    def test_judge_literal_import_is_benign(self) -> None:
        files = {"SKILL.md": SKILL, "scripts/a.py": "m = __import__('json')"}
        verdict = self.code_lens(files, RuleId.DANGEROUS_INSTRUCTIONS, "python_dynamic")
        self.assertEqual(verdict, LensVerdict.BENIGN)

    def test_judge_built_import_is_a_risk(self) -> None:
        files = {"SKILL.md": SKILL, "scripts/a.py": "m = __import__('w%d' % 1)"}
        verdict = self.code_lens(files, RuleId.DANGEROUS_INSTRUCTIONS, "python_dynamic")
        self.assertEqual(verdict, LensVerdict.RISK)

    def test_judge_exec_is_a_risk(self) -> None:
        files = {"SKILL.md": SKILL, "scripts/a.py": "exec('x = 1')"}
        verdict = self.code_lens(files, RuleId.DANGEROUS_INSTRUCTIONS, "python_dynamic")
        self.assertEqual(verdict, LensVerdict.RISK)

    def test_xmlns_namespace_is_not_a_plain_link(self) -> None:
        svg = '<svg xmlns="' + "http" + '://www.w3.org/2000/svg"></svg>'
        files = {"SKILL.md": SKILL, "assets/icon.svg": svg}
        self.assertNotIn("plain_link", check_ids(files, RuleId.MALICIOUS_REFERENCES))

    def test_other_w3_link_is_still_a_plain_link(self) -> None:
        html = '<a href="' + "http" + '://www.w3.org/TR/">spec</a>'
        files = {"SKILL.md": SKILL, "assets/a.html": html}
        self.assertIn("plain_link", check_ids(files, RuleId.MALICIOUS_REFERENCES))

    def test_judge_model_file_is_a_risk(self) -> None:
        files = {"SKILL.md": SKILL, "assets/model.onnx": b"\x08\x01"}
        verdict = self.code_lens(files, RuleId.OBFUSCATED_INTENT, "unknown_type")
        self.assertEqual(verdict, LensVerdict.RISK)


class TestNewChecks(unittest.TestCase):
    def test_run_exec_in_markdown_code_block_errors(self) -> None:
        body = SKILL + "```python\n" + EXEC_SRC + "\n```\n"
        self.assertIn(
            "markdown_dynamic_code",
            check_ids({"SKILL.md": body}, RuleId.DANGEROUS_INSTRUCTIONS),
        )

    def test_run_exec_in_markdown_prose_is_not_a_code_block_finding(self) -> None:
        body = SKILL + "Never call " + EXEC_SRC + " on input.\n"
        self.assertNotIn(
            "markdown_dynamic_code",
            check_ids({"SKILL.md": body}, RuleId.DANGEROUS_INSTRUCTIONS),
        )

    def test_run_real_png_data_uri_passes(self) -> None:
        html = '<img src="data:image/png;base64,iVBORw0KGgo=">'
        files = {"SKILL.md": SKILL, "assets/a.html": html}
        self.assertNotIn("embedded_media", check_ids(files, RuleId.OBFUSCATED_INTENT))
        self.assertNotIn("encoded_base64", check_ids(files, RuleId.OBFUSCATED_INTENT))

    def test_run_mislabeled_data_uri_errors(self) -> None:
        html = '<img src="data:image/png;base64,' + "QUJD" * 40 + '">'
        files = {"SKILL.md": SKILL, "assets/a.html": html}
        self.assertIn("embedded_media", check_ids(files, RuleId.OBFUSCATED_INTENT))

    def test_signature_matches_real_files_of_each_type(self) -> None:
        samples = {
            "image/png": bytes.fromhex("89504e470d0a1a0a") + b"rest",
            "image/webp": b"RIFF\x10\x00\x00\x00WEBPVP8 ",
            "video/mp4": b"\x00\x00\x00\x18ftypmp42rest",
            "audio/wav": b"RIFF\x24\x00\x00\x00WAVEfmt ",
        }
        for media, data in samples.items():
            payload = base64.b64encode(data).decode("ascii")
            with self.subTest(media=media):
                self.assertEqual(MediaPayload(media, payload).problem([media]), "")

    def test_signature_rejects_another_type(self) -> None:
        payload = base64.b64encode(b"GIF89a-not-a-png").decode("ascii")
        problem = MediaPayload("image/png", payload).problem(["image/png"])
        self.assertEqual(problem, "the bytes are not image/png")

    def test_base64_svg_is_a_finding(self) -> None:
        payload = base64.b64encode(b"<svg></svg>").decode("ascii")
        problem = MediaPayload("image/svg+xml", payload).problem(["image/svg+xml"])
        self.assertIn("embed the SVG as text", problem)

    def test_run_split_parts_and_oversize_skill_error(self) -> None:
        files = {
            "SKILL.md": SKILL,
            "assets/w.part00": "x",
            "assets/big.md": "x " * 1_100_000,
        }
        ids = check_ids(files, RuleId.OBFUSCATED_INTENT)
        self.assertIn("split_file", ids)
        self.assertIn("skill_size", ids)

    def test_run_evals_are_not_counted_in_skill_size(self) -> None:
        files = {"SKILL.md": SKILL, "evals/files/big.md": "x " * 1_100_000}
        self.assertNotIn("skill_size", check_ids(files, RuleId.OBFUSCATED_INTENT))

    def test_run_package_outside_manifest_errors(self) -> None:
        files = {"SKILL.md": SKILL, "scripts/a.py": "import onnxruntime\nimport numpy"}
        results = [
            r
            for r in found(files, RuleId.SUPPLY_CHAIN)
            if r.check_id == "python_third_party"
        ]
        self.assertEqual([r.quote for r in results], ["onnxruntime"])
        self.assertEqual(results[0].status, Status.CONFIRMED)

    def test_run_docstring_is_not_a_long_literal(self) -> None:
        source = '"""' + "x" * 5000 + '"""\nX = 1\n'
        files = {"SKILL.md": SKILL, "scripts/a.py": source}
        self.assertNotIn(
            "python_long_literal", check_ids(files, RuleId.OBFUSCATED_INTENT)
        )

    def test_run_unbounded_loop_and_huge_allocation_warn(self) -> None:
        source = WHILE_TRUE + "\n    n = 1\nb = bytes(10**9)\n"
        files = {"SKILL.md": SKILL, "scripts/a.py": source}
        results = found(files, RuleId.RESOURCE_ABUSE)
        self.assertEqual(
            len([r for r in results if r.check_id == "python_resource"]), 2
        )


class TestDismissals(unittest.TestCase):
    def problems(self, result: Result) -> list[str]:
        report = results_with([result], [TestVerdictVerifier.done])
        texts = TestVerdictVerifier.texts
        return [issue.problem for issue in VerdictVerifier(report, texts).verify()]

    def test_verify_dismissal_with_three_benign_lenses_passes(self) -> None:
        result = code_result(
            status=Status.DISMISSED,
            level=Level.ERROR,
            lenses=[lens(item, LensVerdict.BENIGN) for item in Lens],
        )
        self.assertEqual(self.problems(result), [])

    def test_verify_dismissal_without_reviewer_fails(self) -> None:
        result = code_result(
            status=Status.DISMISSED,
            level=Level.WARNING,
            lenses=[
                lens(Lens.CODE, LensVerdict.UNCLEAR),
                lens(Lens.AGENT, LensVerdict.BENIGN),
            ],
        )
        self.assertEqual(
            self.problems(result), ["dismissed without a benign verdict from: reviewer"]
        )

    def test_verify_error_needs_a_benign_code_lens(self) -> None:
        result = code_result(
            status=Status.DISMISSED,
            level=Level.ERROR,
            lenses=[
                lens(Lens.CODE, LensVerdict.UNCLEAR),
                lens(Lens.AGENT, LensVerdict.BENIGN),
                lens(Lens.REVIEWER, LensVerdict.BENIGN),
            ],
        )
        self.assertEqual(
            self.problems(result),
            ["an error can be dismissed only when the code lens also finds it benign"],
        )

    def test_verify_any_risk_lens_blocks_dismissal(self) -> None:
        result = code_result(
            status=Status.DISMISSED,
            lenses=[
                lens(Lens.CODE, LensVerdict.RISK),
                lens(Lens.AGENT, LensVerdict.BENIGN),
                lens(Lens.REVIEWER, LensVerdict.BENIGN),
            ],
        )
        self.assertTrue(self.problems(result)[0].startswith("a lens found a risk"))

    def test_verify_guard_catches_removed_or_downgraded_code_results(self) -> None:
        fresh = code_result(status=Status.CONFIRMED, level=Level.ERROR)
        self.assertEqual(
            [i.problem for i in CodeResultsGuard([], [fresh]).verify()],
            ["code result removed"],
        )
        lowered = fresh.model_copy(update={"level": Level.WARNING})
        self.assertEqual(
            [i.problem for i in CodeResultsGuard([lowered], [fresh]).verify()],
            ["code result level or code lens changed"],
        )


def accept(result: Result) -> Acceptance:
    return Acceptance(
        rule_id=result.rule_id,
        path=result.path,
        line=result.line,
        quote=result.quote,
        date="2026-11-20",
    )


class TestPendingDecisions(unittest.TestCase):
    def pending(
        self, results: list[Result], acceptances: list[Acceptance] | None = None
    ) -> list[str]:
        report = results_with(results, [TestVerdictVerifier.done]).model_copy(
            update={"acceptances": acceptances or []}
        )
        return [d.problem for d in PendingDecisions(report).list()]

    def test_confirmed_finding_waits_until_accepted(self) -> None:
        self.assertEqual(
            self.pending([agent_result()]),
            ["confirmed: the user fixes or accepts it"],
        )

    def test_accepted_finding_is_not_pending(self) -> None:
        finding = agent_result()
        self.assertEqual(self.pending([finding], [accept(finding)]), [])

    def test_acceptance_of_another_line_does_not_count(self) -> None:
        moved = accept(agent_result(line=9))
        self.assertEqual(
            self.pending([agent_result()], [moved]),
            ["confirmed: the user fixes or accepts it"],
        )

    def test_no_findings_means_nothing_pending(self) -> None:
        self.assertEqual(self.pending([]), [])

    def test_acceptance_records_no_name(self) -> None:
        self.assertNotIn("accepted_by", Acceptance.model_fields)

    def test_unsure_finding_waits_for_the_user(self) -> None:
        unsure = agent_result(status=Status.UNSURE)
        self.assertIn("unsure: the user must decide", self.pending([unsure]))

    def test_report_warns_and_marks_an_accepted_finding(self) -> None:
        finding = agent_result()
        report = results_with([finding], [TestVerdictVerifier.done]).model_copy(
            update={"acceptances": [accept(finding)]}
        )
        text = ReportBuilder(report, BY_ID).build()
        self.assertIn("The user accepted 1 finding", text)
        self.assertIn("| yes |", text)
        self.assertNotIn("lock", text.lower())


class TestKindsCovered(unittest.TestCase):
    def test_every_kind_is_used_by_a_rule(self) -> None:
        used = {check.kind for rule in RULES for check in rule.checks}
        self.assertEqual(used, set(CheckKind))

    def test_example_paths_are_plain_names(self) -> None:
        for rule in RULES:
            for check in rule.checks:
                with self.subTest(check=f"{rule.id}.{check.id}"):
                    self.assertNotIn("*", PurePosixPath(example_path(check)).name)


if __name__ == "__main__":
    unittest.main()
