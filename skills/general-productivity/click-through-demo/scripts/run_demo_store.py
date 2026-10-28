"""
description: Own the click-through demo's data file (demo.json), which the agent changes through change sets and the user may also edit by hand. Applies a validated JSON change set (demo fields, chapters, steps with hotspots, media, blur areas, page-load timings, trimming) as one all-or-nothing write, and exports the snapshot JSON that create_demo.py builds from. Call main(["--store", "<demo.json>", "apply", "--changes", "<changes.json>"]), main(["--store", "<demo.json>", "export", "--out", "<snapshot.json>"]), or main(["--store", "<demo.json>", "show"]).
last_updated: 2026-10-27
origin: original
"""

import argparse
import datetime
import logging
import sys
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


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

EDGE_TOLERANCE = 0.5
MAX_ZOOM = 3.0
STORE_VERSION = 1
TEMP_SUFFIX = ".tmp"
DEMO_FIELDS = (
    "title",
    "start_url",
    "goal",
    "intro_title",
    "intro_body",
    "outro_title",
    "outro_body",
    "cta_label",
    "cta_url",
    "accent",
)
STEP_TEXT_FIELDS = (
    "chapter",
    "title",
    "caption",
    "action",
    "url",
    "screenshot",
    "load_ms",
)
REQUIRED_NEW_STEP = ("title", "caption", "url", "screenshot")


class StrictModel(BaseModel):
    """Rejects unknown fields, so a misspelled key in a hand-edited demo.json is reported, not ignored."""

    model_config = ConfigDict(extra="forbid")


class DemoStoreError(ValueError):
    """A change set or stored demo the demo cannot be built from."""


class Operation(StrEnum):
    APPLY = "apply"
    EXPORT = "export"
    SHOW = "show"


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO_LINK = "video_link"
    VIDEO_FILE = "video_file"


class Rect(StrictModel):
    """A rectangle in viewport percentages (0 to 100)."""

    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    w: float = Field(gt=0, le=100)
    h: float = Field(gt=0, le=100)

    @model_validator(mode="after")
    def _inside_screen(self) -> Self:
        if (
            self.x + self.w > 100 + EDGE_TOLERANCE
            or self.y + self.h > 100 + EDGE_TOLERANCE
        ):
            raise ValueError("rectangle extends past the edge of the screenshot")
        return self


class Hotspot(Rect):
    """The element the viewer clicks next, with an optional zoom factor."""

    zoom: float = Field(default=1.0, ge=1.0, le=MAX_ZOOM)


class BlurArea(Rect):
    """An area whose pixels are destroyed in the built demo."""

    reason: str = ""


class MediaItem(StrictModel):
    """An image or video shown in a step's caption card."""

    kind: MediaKind
    src: str = Field(min_length=1)
    caption: str = ""


class ChapterIn(StrictModel):
    position: int = Field(ge=1)
    title: str = Field(min_length=1)


class DemoChange(StrictModel):
    """Demo-level fields. Only the fields present are changed."""

    title: str | None = None
    start_url: str | None = None
    goal: str | None = None
    intro_title: str | None = None
    intro_body: str | None = None
    outro_title: str | None = None
    outro_body: str | None = None
    cta_label: str | None = None
    cta_url: str | None = None
    accent: str | None = None


class StepChange(StrictModel):
    """Create or update the step at a position. Absent fields keep their value."""

    position: int = Field(ge=1)
    chapter: int | None = None
    title: str | None = None
    caption: str | None = None
    action: str | None = None
    url: str | None = None
    screenshot: str | None = None
    load_ms: int | None = Field(default=None, ge=0)
    hotspot: Hotspot | None = None
    clear_hotspot: bool = False
    media: list[MediaItem] | None = None
    blurs: list[BlurArea] | None = None


class LoadEvent(StrictModel):
    """One wait-for-ready result, kept so slow pages can be reviewed later."""

    step: int = Field(ge=1)
    ready: bool
    waited_ms: int = Field(ge=0)
    detail: str = ""


class ChangeSet(StrictModel):
    """Everything one apply call may change. Lists replace a step's media or blurs."""

    demo: DemoChange | None = None
    chapters: list[ChapterIn] = Field(default_factory=list)
    steps: list[StepChange] = Field(default_factory=list)
    delete_steps_from: int | None = Field(default=None, ge=1)
    load_events: list[LoadEvent] = Field(default_factory=list)


class StoredDemo(StrictModel):
    """The demo-level record kept in demo.json."""

    title: str = Field(min_length=1)
    start_url: str = Field(min_length=1)
    goal: str = ""
    intro_title: str | None = None
    intro_body: str | None = None
    outro_title: str | None = None
    outro_body: str | None = None
    cta_label: str | None = None
    cta_url: str | None = None
    accent: str | None = None
    created_at: str
    updated_at: str


class StoredStep(StrictModel):
    """One captured step as kept in demo.json."""

    position: int = Field(ge=1)
    chapter: int | None = None
    title: str
    caption: str
    action: str = ""
    url: str
    screenshot: str
    load_ms: int | None = None
    hotspot: Hotspot | None = None
    media: list[MediaItem] = Field(default_factory=list)
    blurs: list[BlurArea] = Field(default_factory=list)
    captured_at: str


class StoredLoadEvent(LoadEvent):
    logged_at: str


class DemoStore(StrictModel):
    """The whole contents of demo.json. An empty store means no demo yet."""

    version: int = STORE_VERSION
    demo: StoredDemo | None = None
    chapters: list[ChapterIn] = Field(default_factory=list)
    steps: list[StoredStep] = Field(default_factory=list)
    load_log: list[StoredLoadEvent] = Field(default_factory=list)


class ApplyResult(StrictModel):
    steps: int
    chapters: int


class SnapshotStep(StrictModel):
    position: int
    chapter: int | None
    title: str
    caption: str
    action: str
    url: str
    screenshot: str
    load_ms: int | None
    hotspot: Hotspot | None
    media: list[MediaItem]
    blurs: list[BlurArea]


class DemoSnapshot(StrictModel):
    """The whole demo as create_demo.py consumes it."""

    title: str
    start_url: str
    goal: str
    intro_title: str | None
    intro_body: str | None
    outro_title: str | None
    outro_body: str | None
    cta_label: str | None
    cta_url: str | None
    accent: str | None
    chapters: list[ChapterIn]
    steps: list[SnapshotStep]

    @model_validator(mode="after")
    def _buildable(self) -> Self:
        if not self.steps:
            raise ValueError("the demo has no steps yet")
        positions = [step.position for step in self.steps]
        if positions != list(range(1, len(positions) + 1)):
            raise ValueError(
                f"step positions must run 1..{len(positions)} with no gaps, got {positions}"
            )
        chapter_positions = {chapter.position for chapter in self.chapters}
        for step in self.steps:
            if step.chapter is not None and step.chapter not in chapter_positions:
                raise ValueError(
                    f"step {step.position} uses chapter {step.chapter}, which does not exist"
                )
        for step in self.steps[:-1]:
            if step.hotspot is None:
                raise ValueError(
                    f"step {step.position} has no hotspot; every step except the last "
                    "must highlight what the viewer clicks next"
                )
        return self


for _model in (
    StrictModel,
    Rect,
    Hotspot,
    BlurArea,
    MediaItem,
    ChapterIn,
    DemoChange,
    StepChange,
    LoadEvent,
    ChangeSet,
    StoredDemo,
    StoredStep,
    StoredLoadEvent,
    DemoStore,
    ApplyResult,
    SnapshotStep,
    DemoSnapshot,
):
    _model.model_rebuild()


class StoreFile:
    """Reads and writes demo.json (I/O). A write lands whole or not at all."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> DemoStore:
        """Return the stored demo, or an empty store when the file does not exist yet."""
        if not self.path.exists():
            return DemoStore()
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as error:
            raise DemoStoreError(f"cannot read {self.path}: {error}") from error
        try:
            return DemoStore.model_validate_json(raw)
        except ValidationError as error:
            raise DemoStoreError(
                f"{self.path} is not a valid demo file: {error}"
            ) from error

    def save(self, store: DemoStore) -> None:
        """Write to a temporary file beside demo.json, then swap it into place."""
        if not self.path.parent.is_dir():
            raise DemoStoreError(f"folder does not exist: {self.path.parent}")
        temporary = self.path.with_name(self.path.name + TEMP_SUFFIX)
        try:
            temporary.write_text(
                store.model_dump_json(indent=2), encoding="utf-8", newline="\n"
            )
            temporary.replace(self.path)
        except OSError as error:
            raise DemoStoreError(f"cannot write {self.path}: {error}") from error


class ChangeApplier:
    """Applies a change set to a stored demo and returns the new version (pure)."""

    def __init__(self, store: DemoStore, changes: ChangeSet, now: str) -> None:
        self.store = store
        self.changes = changes
        self.now = now

    def apply(self) -> DemoStore:
        """Return the updated store, or raise DemoStoreError and change nothing."""
        demo = self._apply_demo(self.store.demo, self.changes.demo)
        if demo is None:
            raise DemoStoreError(
                "create the demo first: the first change set needs demo.title and demo.start_url"
            )
        chapters = {chapter.position: chapter for chapter in self.store.chapters}
        for chapter in self.changes.chapters:
            chapters[chapter.position] = chapter
        steps = {step.position: step for step in self.store.steps}
        for change in self.changes.steps:
            steps[change.position] = self._apply_step(
                steps.get(change.position), change
            )
        if self.changes.delete_steps_from is not None:
            cut = self.changes.delete_steps_from
            steps = {
                position: step for position, step in steps.items() if position < cut
            }
            if cut - 1 in steps:
                steps[cut - 1] = steps[cut - 1].model_copy(update={"action": ""})
            used = {step.chapter for step in steps.values()}
            chapters = {
                position: chapter
                for position, chapter in chapters.items()
                if position in used
            }
        load_log = list(self.store.load_log) + [
            StoredLoadEvent(**event.model_dump(), logged_at=self.now)
            for event in self.changes.load_events
        ]
        updated = DemoStore(
            demo=demo.model_copy(update={"updated_at": self.now}),
            chapters=[chapters[position] for position in sorted(chapters)],
            steps=[steps[position] for position in sorted(steps)],
            load_log=load_log,
        )
        try:
            return DemoStore.model_validate(updated.model_dump())
        except ValidationError as error:
            raise DemoStoreError(
                f"the change set leaves an invalid demo: {error}"
            ) from error

    def _apply_demo(
        self, current: StoredDemo | None, change: DemoChange | None
    ) -> StoredDemo | None:
        values = change.model_dump(exclude_none=True) if change is not None else {}
        if current is None:
            if not values:
                return None
            if not values.get("title") or not values.get("start_url"):
                raise DemoStoreError("a new demo needs a title and a start_url")
            return StoredDemo(**values, created_at=self.now, updated_at=self.now)
        return current.model_copy(
            update={
                field: value for field, value in values.items() if field in DEMO_FIELDS
            }
        )

    def _apply_step(
        self, existing: StoredStep | None, change: StepChange
    ) -> StoredStep:
        values = {
            field: getattr(change, field)
            for field in STEP_TEXT_FIELDS
            if getattr(change, field) is not None
        }
        if existing is None:
            missing = [field for field in REQUIRED_NEW_STEP if field not in values]
            if missing:
                raise DemoStoreError(
                    f"new step {change.position} is missing {', '.join(missing)}"
                )
            existing = StoredStep(
                position=change.position, captured_at=self.now, **values
            )
        update: dict = dict(values)
        if change.hotspot is not None:
            update["hotspot"] = change.hotspot
        elif change.clear_hotspot:
            update["hotspot"] = None
        if change.media is not None:
            update["media"] = list(change.media)
        if change.blurs is not None:
            update["blurs"] = list(change.blurs)
        return existing.model_copy(update=update)


class SnapshotReader:
    """Turns a stored demo into a validated DemoSnapshot (pure)."""

    def __init__(self, store: DemoStore) -> None:
        self.store = store

    def read(self) -> DemoSnapshot:
        """Return the snapshot, or raise DemoStoreError naming what blocks a build."""
        demo = self.store.demo
        if demo is None:
            raise DemoStoreError("the file has no demo yet")
        steps = [
            SnapshotStep(
                position=step.position,
                chapter=step.chapter,
                title=step.title,
                caption=step.caption,
                action=step.action,
                url=step.url,
                screenshot=step.screenshot,
                load_ms=step.load_ms,
                hotspot=step.hotspot,
                media=step.media,
                blurs=step.blurs,
            )
            for step in sorted(self.store.steps, key=lambda item: item.position)
        ]
        used = {step.chapter for step in steps}
        chapters = [
            chapter
            for chapter in sorted(self.store.chapters, key=lambda item: item.position)
            if chapter.position in used
        ]
        try:
            return DemoSnapshot(
                **{field: getattr(demo, field) for field in DEMO_FIELDS},
                chapters=chapters,
                steps=steps,
            )
        except ValidationError as error:
            raise DemoStoreError(f"the demo cannot be built yet: {error}") from error


class SummaryFormatter:
    """Formats a snapshot as short lines for the agent to read (pure)."""

    def __init__(self, snapshot: DemoSnapshot) -> None:
        self.snapshot = snapshot

    def render(self) -> list[str]:
        """Return one header line and one line per step."""
        chapters = {
            chapter.position: chapter.title for chapter in self.snapshot.chapters
        }
        lines = [
            f"{self.snapshot.title}: {len(self.snapshot.steps)} steps, {len(chapters)} chapters"
        ]
        for step in self.snapshot.steps:
            chapter = (
                chapters.get(step.chapter, "-") if step.chapter is not None else "-"
            )
            spot = "hotspot" if step.hotspot else "no hotspot"
            lines.append(
                f"{step.position}. [{chapter}] {step.title} | {spot} | load {step.load_ms} ms | "
                f"{len(step.media)} media | {len(step.blurs)} blurs | action: {step.action or '-'}"
            )
        return lines


class ChangeSetReader:
    """Reads and validates a change-set JSON file (I/O at the boundary)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> ChangeSet:
        """Return the parsed change set or raise DemoStoreError."""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as error:
            raise DemoStoreError(f"cannot read {self.path}: {error}") from error
        try:
            return ChangeSet.model_validate_json(raw)
        except ValidationError as error:
            raise DemoStoreError(f"{self.path} is invalid: {error}") from error


class DemoStoreCommand:
    """Facade: run one operation against demo.json and return lines to log."""

    def __init__(
        self, store_path: Path, operation: Operation, file_path: Path | None
    ) -> None:
        self.store_path = store_path
        self.operation = operation
        self.file_path = file_path

    def run(self) -> list[str]:
        """Apply, export, or show, and describe what happened."""
        store_file = StoreFile(self.store_path)
        store = store_file.load()
        if self.operation is Operation.APPLY:
            if self.file_path is None:
                raise DemoStoreError("apply needs --changes")
            changes = ChangeSetReader(self.file_path).read()
            now = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
            updated = ChangeApplier(store, changes, now).apply()
            store_file.save(updated)
            result = ApplyResult(
                steps=len(updated.steps), chapters=len(updated.chapters)
            )
            return [f"applied: {result.steps} steps, {result.chapters} chapters"]
        snapshot = SnapshotReader(store).read()
        if self.operation is Operation.EXPORT:
            if self.file_path is None:
                raise DemoStoreError("export needs --out")
            self.file_path.write_text(
                snapshot.model_dump_json(indent=2), encoding="utf-8", newline="\n"
            )
            return [f"exported {len(snapshot.steps)} steps to {self.file_path}"]
        return SummaryFormatter(snapshot).render()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage a click-through demo's data file (demo.json)."
    )
    parser.add_argument(
        "--store", required=True, help="Path to demo.json (created on the first apply)."
    )
    sub = parser.add_subparsers(dest="operation", required=True)
    apply_parser = sub.add_parser(
        Operation.APPLY.value, help="Apply a change-set JSON file."
    )
    apply_parser.add_argument(
        "--changes", required=True, help="Path to the change-set JSON."
    )
    export_parser = sub.add_parser(
        Operation.EXPORT.value, help="Write the build snapshot JSON."
    )
    export_parser.add_argument("--out", required=True, help="Path for snapshot.json.")
    sub.add_parser(Operation.SHOW.value, help="Log a one-line summary per step.")
    args = parser.parse_args(argv)

    operation = Operation(args.operation)
    file_arg = getattr(args, "changes", None) or getattr(args, "out", None)
    file_path = Path(file_arg) if file_arg else None
    try:
        lines = DemoStoreCommand(Path(args.store), operation, file_path).run()
    except DemoStoreError as error:
        logger.error("%s", error)
        return 1
    for line in lines:
        logger.info("%s", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
