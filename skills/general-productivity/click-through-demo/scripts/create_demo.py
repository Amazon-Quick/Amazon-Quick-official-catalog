"""
description: Build the single-file click-through demo (index.html) and a hotspot check image (hotspot-check.png) from the snapshot JSON that run_demo_store.py exports. Destroys the pixels under every blur area, embeds screenshots at full resolution by default, embeds image and video files, plays direct https video links and reports the file size. Call main(["--snapshot", "<snapshot.json>", "--template", "<demo-template.html>", "--out-dir", "<folder>"]).
last_updated: 2026-10-27
origin: original
"""

import argparse
import base64
import html
import io
import json
import logging
import re
import sys
from enum import StrEnum
from pathlib import Path
from typing import Self
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFilter
from pydantic import BaseModel, Field, ValidationError, model_validator


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

DEFAULT_QUALITY = 90
PIXELATE_BLOCK = 24
BLUR_RADIUS = 18
CHECK_TILE_WIDTH = 1024
CHECK_COLUMNS = 2
HOTSPOT_OUTLINE = (255, 0, 255)
BLUR_OUTLINE = (0, 170, 255)
CHECK_LINE_WIDTH = 3
CHECK_BACKGROUND = (255, 255, 255)
DATA_PLACEHOLDER = "__DEMO_DATA__"
TITLE_PLACEHOLDER = "__DEMO_TITLE__"
HTML_NAME = "index.html"
CHECK_NAME = "hotspot-check.png"
DEFAULT_ACCENT = "#7c3aed"
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
VIDEO_MIME = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/mp4"}


class DemoBuildError(ValueError):
    """The snapshot, a screenshot, or a media item cannot be built."""


class ImageFormat(StrEnum):
    WEBP = "webp"
    JPEG = "jpeg"


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO_LINK = "video_link"
    VIDEO_FILE = "video_file"


class RenderKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class Rect(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    w: float = Field(gt=0, le=100)
    h: float = Field(gt=0, le=100)


class Hotspot(Rect):
    zoom: float = Field(default=1.0, ge=1.0, le=3.0)


class BlurArea(Rect):
    reason: str = ""


class MediaItem(BaseModel):
    kind: MediaKind
    src: str = Field(min_length=1)
    caption: str = ""


class Chapter(BaseModel):
    position: int
    title: str


class SnapshotStep(BaseModel):
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


class DemoSnapshot(BaseModel):
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
    chapters: list[Chapter]
    steps: list[SnapshotStep] = Field(min_length=1)

    @model_validator(mode="after")
    def _non_final_steps_have_hotspots(self) -> Self:
        for step in self.steps[:-1]:
            if step.hotspot is None:
                raise ValueError(f"step {step.position} has no hotspot")
        return self


class BuildOptions(BaseModel):
    max_width: int = Field(default=0, ge=0)
    quality: int = Field(default=DEFAULT_QUALITY, ge=40, le=100)
    image_format: ImageFormat = ImageFormat.WEBP


class RenderedMedia(BaseModel):
    kind: RenderKind
    src: str
    caption: str


class RenderedStep(BaseModel):
    title: str
    caption: str
    action: str
    url: str
    chapter: int | None
    image: str
    width: int
    height: int
    hotspot: Hotspot | None
    media: list[RenderedMedia]


class DemoResult(BaseModel):
    """What a build produced. Paths are strings because the sandbox replaces Path."""

    html_path: str
    check_path: str
    steps: int
    megabytes: float


for _model in (
    Rect,
    Hotspot,
    BlurArea,
    MediaItem,
    Chapter,
    SnapshotStep,
    DemoSnapshot,
    BuildOptions,
    RenderedMedia,
    RenderedStep,
    DemoResult,
):
    _model.model_rebuild()


class SnapshotReader:
    """Reads and validates snapshot.json (I/O at the boundary)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> DemoSnapshot:
        """Return the snapshot or raise DemoBuildError."""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as error:
            raise DemoBuildError(f"cannot read {self.path}: {error}") from error
        try:
            return DemoSnapshot.model_validate_json(raw)
        except ValidationError as error:
            raise DemoBuildError(f"{self.path} is invalid: {error}") from error


class FileLoader:
    """Reads one file's bytes (I/O)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> bytes:
        """Return the bytes or raise DemoBuildError."""
        try:
            return self.path.read_bytes()
        except OSError as error:
            raise DemoBuildError(f"cannot read {self.path}: {error}") from error


class BlurApplier:
    """Destroys the pixels under each blur area: pixelate, then blur (pure)."""

    def __init__(self, image: Image.Image, areas: list[BlurArea]) -> None:
        self.image = image
        self.areas = areas

    def apply(self) -> Image.Image:
        """Return a copy with every area unrecoverable."""
        result = self.image.copy()
        for area in self.areas:
            box = (
                round(area.x / 100 * result.width),
                round(area.y / 100 * result.height),
                round(min(100.0, area.x + area.w) / 100 * result.width),
                round(min(100.0, area.y + area.h) / 100 * result.height),
            )
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            region = result.crop(box)
            small = region.resize(
                (
                    max(1, region.width // PIXELATE_BLOCK),
                    max(1, region.height // PIXELATE_BLOCK),
                ),
                Image.BILINEAR,
            )
            region = small.resize(region.size, Image.NEAREST).filter(
                ImageFilter.GaussianBlur(BLUR_RADIUS)
            )
            result.paste(region, box[:2])
        return result


class ImageEncoder:
    """Encodes an image as a data URI, shrinking it only when max_width asks (pure)."""

    def __init__(self, image: Image.Image, options: BuildOptions) -> None:
        self.image = image
        self.options = options

    def encode(self) -> str:
        """Return the data URI."""
        image = self.image
        if self.options.max_width and image.width > self.options.max_width:
            height = round(image.height * self.options.max_width / image.width)
            image = image.resize((self.options.max_width, height), Image.LANCZOS)
        buffer = io.BytesIO()
        if self.options.image_format is ImageFormat.WEBP:
            image.save(buffer, "WEBP", quality=self.options.quality, method=6)
            mime = "image/webp"
        else:
            image.save(buffer, "JPEG", quality=self.options.quality, optimize=True)
            mime = "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(buffer.getvalue()).decode(
            "ascii"
        )


class VideoLinkResolver:
    """Checks that a video link is a direct https video file the page can play (pure)."""

    def __init__(self, link: str) -> None:
        self.link = link

    def resolve(self) -> RenderedMedia:
        """Return a video media item, or raise DemoBuildError."""
        parsed = urlparse(self.link)
        if parsed.scheme != "https":
            raise DemoBuildError(f"video links must use https: {self.link}")
        if Path(parsed.path).suffix.lower() in VIDEO_MIME:
            return RenderedMedia(kind=RenderKind.VIDEO, src=self.link, caption="")
        raise DemoBuildError(
            f"unsupported video link (use a direct https .mp4 or .webm link, or embed the file): {self.link}"
        )


class MediaRenderer:
    """Turns one media item into something the page can show (pure: file bytes are injected)."""

    def __init__(self, item: MediaItem, file_bytes: bytes | None) -> None:
        self.item = item
        self.file_bytes = file_bytes

    def render(self) -> RenderedMedia:
        """Return the rendered media, or raise DemoBuildError."""
        item = self.item
        if item.kind is MediaKind.VIDEO_LINK:
            return (
                VideoLinkResolver(item.src)
                .resolve()
                .model_copy(update={"caption": item.caption})
            )
        if item.src.startswith("https://"):
            kind = (
                RenderKind.IMAGE if item.kind is MediaKind.IMAGE else RenderKind.VIDEO
            )
            return RenderedMedia(kind=kind, src=item.src, caption=item.caption)
        table = IMAGE_MIME if item.kind is MediaKind.IMAGE else VIDEO_MIME
        mime = table.get(Path(item.src).suffix.lower())
        if mime is None:
            raise DemoBuildError(f"unsupported {item.kind.value} file type: {item.src}")
        if self.file_bytes is None:
            raise DemoBuildError(f"no file contents for {item.src}")
        kind = RenderKind.IMAGE if item.kind is MediaKind.IMAGE else RenderKind.VIDEO
        uri = f"data:{mime};base64," + base64.b64encode(self.file_bytes).decode("ascii")
        return RenderedMedia(kind=kind, src=uri, caption=item.caption)


class PageBuilder:
    """Fills the HTML template with the demo data (pure)."""

    def __init__(
        self, template: str, snapshot: DemoSnapshot, steps: list[RenderedStep]
    ) -> None:
        self.template = template
        self.snapshot = snapshot
        self.steps = steps

    def build(self) -> str:
        """Return the finished HTML document."""
        if (
            DATA_PLACEHOLDER not in self.template
            or TITLE_PLACEHOLDER not in self.template
        ):
            raise ValueError("template is missing a placeholder")
        snap = self.snapshot
        accent = (
            snap.accent
            if snap.accent and HEX_COLOR_RE.match(snap.accent)
            else DEFAULT_ACCENT
        )
        cta_url = (
            snap.cta_url
            if snap.cta_url and snap.cta_url.startswith(("https://", "http://"))
            else None
        )
        payload = {
            "title": snap.title,
            "accent": accent,
            "intro": {"title": snap.intro_title, "body": snap.intro_body or ""}
            if snap.intro_title
            else None,
            "outro": {
                "title": snap.outro_title,
                "body": snap.outro_body or "",
                "cta_label": snap.cta_label if cta_url else None,
                "cta_url": cta_url,
            }
            if snap.outro_title
            else None,
            "chapters": [chapter.model_dump() for chapter in snap.chapters],
            "steps": [step.model_dump(mode="json") for step in self.steps],
        }
        # Escaping "<" keeps page-derived text from closing the script element.
        data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
        return self.template.replace(
            TITLE_PLACEHOLDER, html.escape(snap.title)
        ).replace(DATA_PLACEHOLDER, data)


class CheckSheetBuilder:
    """Draws hotspots (magenta) and blur areas (blue) on each screenshot and tiles them (pure)."""

    def __init__(self, images: list[Image.Image], steps: list[SnapshotStep]) -> None:
        self.images = images
        self.steps = steps

    def build(self) -> Image.Image:
        """Return the tiled check image."""
        if len(self.images) != len(self.steps):
            raise ValueError("images and steps must be the same length")
        tiles = [
            self._tile(image, step)
            for image, step in zip(self.images, self.steps, strict=True)
        ]
        tile_height = max(tile.height for tile in tiles)
        rows = (len(tiles) + CHECK_COLUMNS - 1) // CHECK_COLUMNS
        columns = min(CHECK_COLUMNS, len(tiles))
        sheet = Image.new(
            "RGB", (CHECK_TILE_WIDTH * columns, tile_height * rows), CHECK_BACKGROUND
        )
        for index, tile in enumerate(tiles):
            column = index % CHECK_COLUMNS
            row = index // CHECK_COLUMNS
            sheet.paste(tile, (column * CHECK_TILE_WIDTH, row * tile_height))
        return sheet

    def _tile(self, image: Image.Image, step: SnapshotStep) -> Image.Image:
        height = round(image.height * CHECK_TILE_WIDTH / image.width)
        tile = image.resize((CHECK_TILE_WIDTH, height))
        draw = ImageDraw.Draw(tile)
        for area in step.blurs:
            draw.rectangle(
                self._box(area, height), outline=BLUR_OUTLINE, width=CHECK_LINE_WIDTH
            )
        if step.hotspot is not None:
            draw.rectangle(
                self._box(step.hotspot, height),
                outline=HOTSPOT_OUTLINE,
                width=CHECK_LINE_WIDTH,
            )
        draw.text((8, 8), f"step {step.position}", fill=HOTSPOT_OUTLINE)
        return tile

    def _box(self, rect: Rect, height: int) -> list[float]:
        return [
            rect.x / 100 * CHECK_TILE_WIDTH,
            rect.y / 100 * height,
            (rect.x + rect.w) / 100 * CHECK_TILE_WIDTH,
            (rect.y + rect.h) / 100 * height,
        ]


class DemoBuilder:
    """Facade: read the snapshot, prepare every step, write the page and the check image."""

    def __init__(
        self,
        snapshot_path: Path,
        template_path: Path,
        out_dir: Path,
        options: BuildOptions,
    ) -> None:
        self.snapshot_path = snapshot_path
        self.template_path = template_path
        self.out_dir = out_dir
        self.options = options

    def build(self) -> DemoResult:
        """Build index.html and hotspot-check.png and return what was written."""
        snapshot = SnapshotReader(self.snapshot_path).read()
        base = self.snapshot_path.parent
        originals: list[Image.Image] = []
        rendered: list[RenderedStep] = []
        for step in snapshot.steps:
            with Image.open(
                io.BytesIO(FileLoader(base / step.screenshot).load())
            ) as opened:
                original = opened.convert("RGB")
            originals.append(original)
            protected = BlurApplier(original, step.blurs).apply()
            media = [
                MediaRenderer(item, self._media_bytes(base, item)).render()
                for item in step.media
            ]
            rendered.append(
                RenderedStep(
                    title=step.title,
                    caption=step.caption,
                    action=step.action,
                    url=step.url,
                    chapter=step.chapter,
                    image=ImageEncoder(protected, self.options).encode(),
                    width=original.width,
                    height=original.height,
                    hotspot=step.hotspot,
                    media=media,
                )
            )
        template = self.template_path.read_text(encoding="utf-8")
        page = PageBuilder(template, snapshot, rendered).build()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        html_path = self.out_dir / HTML_NAME
        html_path.write_text(page, encoding="utf-8", newline="\n")
        check_path = self.out_dir / CHECK_NAME
        CheckSheetBuilder(originals, snapshot.steps).build().save(check_path)
        megabytes = round(html_path.stat().st_size / 1_000_000, 2)
        return DemoResult(
            html_path=str(html_path),
            check_path=str(check_path),
            steps=len(snapshot.steps),
            megabytes=megabytes,
        )

    def _media_bytes(self, base: Path, item: MediaItem) -> bytes | None:
        if item.kind is MediaKind.VIDEO_LINK or item.src.startswith("https://"):
            return None
        return FileLoader(base / item.src).load()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a click-through HTML demo from snapshot.json."
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        help="Path to snapshot.json from run_demo_store.py export.",
    )
    parser.add_argument(
        "--template", required=True, help="Path to assets/demo-template.html."
    )
    parser.add_argument(
        "--out-dir", required=True, help="Folder for index.html and hotspot-check.png."
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=0,
        help="Shrink screenshots wider than this; 0 keeps full resolution.",
    )
    parser.add_argument(
        "--quality", type=int, default=DEFAULT_QUALITY, help="Image quality, 40 to 100."
    )
    parser.add_argument(
        "--format",
        default=ImageFormat.WEBP.value,
        choices=[item.value for item in ImageFormat],
    )
    args = parser.parse_args(argv)

    try:
        options = BuildOptions(
            max_width=args.max_width,
            quality=args.quality,
            image_format=ImageFormat(args.format),
        )
        result = DemoBuilder(
            Path(args.snapshot), Path(args.template), Path(args.out_dir), options
        ).build()
    except (DemoBuildError, ValidationError) as error:
        logger.error("%s", error)
        return 1
    logger.info(
        "Built %s: %d steps, %.2f MB; check image %s",
        result.html_path,
        result.steps,
        result.megabytes,
        result.check_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
