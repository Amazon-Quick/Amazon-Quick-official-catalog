"""
description: Create or update the re:Invent morning brief routine from references/routine-morning.md. Builds the routine prompt from the template with the attendee's topics and the day tips of references/day-tips.md, checks that the whole template arrived, then makes one create_scheduled_agent or update_scheduled_agent call with the fixed schedule fields and returns that call's result. In AWS Quick, define everything above main() in one run_python call with tools file_read, create_scheduled_agent, and update_scheduled_agent, then call MorningRoutineSaver(file_read, create_scheduled_agent, update_scheduled_agent).save(RoutineRequest(...)). Run locally as: python create_morning_routine.py <path/to/routine-morning.md> --topics "none chosen" to print the built prompt.
last_updated: 2026-11-23
origin: original

"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

TEMPLATE_PATH = "skills/reinvent-daily-brief/references/routine-morning.md"
DAY_TIPS_PATH = "skills/reinvent-daily-brief/references/day-tips.md"
ROUTINE_NAME = "re:Invent morning brief"
SCHEDULE_TYPE = "cron_like"
SCHEDULE_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ROUTINE_MODEL = "balanced"
FRONTMATTER_DELIMITER = "---"
TOPICS_PLACEHOLDER = "{topics}"
DAY_TIPS_PLACEHOLDER = "{day_tips}"
DAY_TIPS_MARKER = "2026-11-30"
PROMPT_START = "re:Invent morning brief routine, unattended"
PROMPT_END = 'with action "blocked" and the reason.'
REMOVED_LINE = "Work apps:"
TEMPLATE_CHECK_MESSAGE = "template check failed"


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)


class TemplateCheckError(ValueError):
    """Raised when the routine template did not arrive whole."""


class RoutineRequest(BaseModel):
    """The values Workflow - Schedule steps 4 and 7 supply for one create or update call."""

    topics: str
    schedule_time: str
    schedule_timezone: str | None
    tool_policy: list[dict[str, str]] = Field(min_length=1)
    schedule_id: str | None = None


class RoutinePromptBuilder:
    """Pure: turns the template file's text and the topics into the routine prompt."""

    def __init__(self, template_text: str, topics: str, day_tips_text: str) -> None:
        self._template_text = template_text
        self._topics = topics
        self._day_tips = self._tips_block(day_tips_text)

    @staticmethod
    def _tips_block(day_tips_text: str) -> str:
        """The tips file's text after its frontmatter; raise when it is missing or not whole."""
        parts = day_tips_text.split(FRONTMATTER_DELIMITER, 2)
        block = (parts[2] if len(parts) == 3 else "").strip()
        if DAY_TIPS_MARKER not in block or "2026-12-04" not in block:
            raise TemplateCheckError(TEMPLATE_CHECK_MESSAGE)
        return block

    def build(self) -> str:
        """Return the prompt, or raise TemplateCheckError when the template is not whole."""
        parts = self._template_text.split(FRONTMATTER_DELIMITER, 2)
        if len(parts) < 3:
            raise TemplateCheckError(TEMPLATE_CHECK_MESSAGE)
        prompt = (
            parts[2]
            .strip()
            .replace(TOPICS_PLACEHOLDER, self._topics)
            .replace(DAY_TIPS_PLACEHOLDER, self._day_tips)
        )
        if not self._is_whole(prompt):
            raise TemplateCheckError(TEMPLATE_CHECK_MESSAGE)
        return prompt

    @staticmethod
    def _is_whole(prompt: str) -> bool:
        return (
            prompt.startswith(PROMPT_START)
            and prompt.endswith(PROMPT_END)
            and TOPICS_PLACEHOLDER not in prompt
            and DAY_TIPS_PLACEHOLDER not in prompt
            and DAY_TIPS_MARKER in prompt
            and REMOVED_LINE not in prompt
        )


class MorningRoutineSaver:
    """Facade: reads the template, builds the prompt, and makes the one create or update call."""

    def __init__(
        self,
        file_read: Callable[..., Any],
        create_scheduled_agent: Callable[..., Any],
        update_scheduled_agent: Callable[..., Any],
        template_path: str = TEMPLATE_PATH,
        day_tips_path: str = DAY_TIPS_PATH,
    ) -> None:
        self._day_tips_path = day_tips_path
        self._file_read = file_read
        self._create = create_scheduled_agent
        self._update = update_scheduled_agent
        self._template_path = template_path

    def save(self, request: RoutineRequest) -> Any:
        """Create the routine, or update it when request.schedule_id is set, and return the call's result."""
        template_text = self._file_read(path=self._template_path)["content"]
        day_tips_text = self._file_read(path=self._day_tips_path)["content"]
        prompt = RoutinePromptBuilder(
            template_text, request.topics, day_tips_text
        ).build()
        args = self._schedule_args(request)
        if request.schedule_id:
            logger.info("Updating routine %s", request.schedule_id)
            return self._update(schedule_id=request.schedule_id, prompt=prompt, **args)
        logger.info("Creating routine %s", ROUTINE_NAME)
        return self._create(name=ROUTINE_NAME, prompt=prompt, **args)

    @staticmethod
    def _schedule_args(request: RoutineRequest) -> dict[str, Any]:
        args: dict[str, Any] = {
            "schedule_type": SCHEDULE_TYPE,
            "schedule_time": request.schedule_time,
            "schedule_timezone": request.schedule_timezone,
            "schedule_days": list(SCHEDULE_DAYS),
            "tool_policy": request.tool_policy,
            "use_memory": False,
            "allow_subtask_spawning": False,
            "model": ROUTINE_MODEL,
        }
        return {key: value for key, value in args.items() if value is not None}


def main() -> int:
    """Print the prompt built from a local template file, to check it without AWS Quick."""
    parser = argparse.ArgumentParser(
        description="Build the re:Invent morning brief routine prompt."
    )
    parser.add_argument(
        "template", type=Path, help="Path to references/routine-morning.md"
    )
    parser.add_argument(
        "--topics", default="none chosen", help="The Topics: line value"
    )
    parser.add_argument(
        "--day-tips",
        type=Path,
        default=None,
        help="Path to references/day-tips.md (default: next to the template)",
    )
    options = parser.parse_args()
    try:
        tips_path = options.day_tips or options.template.with_name("day-tips.md")
        prompt = RoutinePromptBuilder(
            options.template.read_text(encoding="utf-8"),
            options.topics,
            tips_path.read_text(encoding="utf-8"),
        ).build()
    except (OSError, TemplateCheckError) as error:
        logger.error("Could not build the prompt: %s", error)
        return 1
    print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
