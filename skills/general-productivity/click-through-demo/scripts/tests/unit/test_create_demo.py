"""
description: Unit tests for create_demo.py. Filesystem-free: snapshots, images, media bytes, and templates are built in memory and injected, so video-link checks, media embedding, pixel-destroying blur, full-resolution encoding, page assembly, and the check sheet are verified without disk access.
last_updated: 2026-10-27
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import base64
import io
import json
import unittest

from create_demo import (
    BLUR_OUTLINE,
    CHECK_TILE_WIDTH,
    DEFAULT_ACCENT,
    HOTSPOT_OUTLINE,
    BlurApplier,
    BlurArea,
    BuildOptions,
    CheckSheetBuilder,
    DemoBuildError,
    DemoSnapshot,
    Hotspot,
    ImageEncoder,
    ImageFormat,
    MediaItem,
    MediaKind,
    MediaRenderer,
    PageBuilder,
    RenderedStep,
    RenderKind,
    SnapshotStep,
    VideoLinkResolver,
)
from PIL import Image

TEMPLATE = '<title>__DEMO_TITLE__</title><script type="application/json">__DEMO_DATA__</script>'


def _snapshot_step(
    position: int, hotspot: Hotspot | None, blurs: list[BlurArea] | None = None
) -> SnapshotStep:
    return SnapshotStep(
        position=position,
        chapter=None,
        title="Home",
        caption="The start page.",
        action="",
        url="https://example.com",
        screenshot="screenshots/step-01.png",
        load_ms=None,
        hotspot=hotspot,
        media=[],
        blurs=blurs or [],
    )


def _snapshot(**overrides: object) -> DemoSnapshot:
    fields = {
        "title": "Tour",
        "start_url": "https://example.com",
        "goal": "",
        "intro_title": None,
        "intro_body": None,
        "outro_title": None,
        "outro_body": None,
        "cta_label": None,
        "cta_url": None,
        "accent": None,
        "chapters": [],
        "steps": [_snapshot_step(1, None)],
    }
    fields.update(overrides)
    return DemoSnapshot(**fields)


def _rendered(caption: str) -> RenderedStep:
    return RenderedStep(
        title="Home",
        caption=caption,
        action="Click Docs",
        url="https://example.com",
        chapter=None,
        image="data:image/webp;base64,AAAA",
        width=100,
        height=50,
        hotspot=Hotspot(x=10, y=10, w=5, h=5),
        media=[],
    )


def _payload(page: str) -> dict:
    return json.loads(page.split('json">', 1)[1].rsplit("</script>", 1)[0])


class TestVideoLinkResolver(unittest.TestCase):
    def test_direct_mp4_and_webm_links_play_in_a_video_element(self) -> None:
        for link in (
            "https://example.com/clip.mp4",
            "https://example.com/media/clip.webm?v=2",
        ):
            media = VideoLinkResolver(link).resolve()
            self.assertEqual(media.kind, RenderKind.VIDEO)
            self.assertEqual(media.src, link)

    def test_http_and_page_links_are_rejected(self) -> None:
        for link in (
            "http://example.com/clip.mp4",
            "https://example.com/watch?v=abc",
            "https://example.com/video/123",
        ):
            with self.assertRaises(DemoBuildError):
                VideoLinkResolver(link).resolve()


class TestMediaRenderer(unittest.TestCase):
    def test_image_file_is_embedded_as_data_uri(self) -> None:
        media = MediaRenderer(
            MediaItem(kind=MediaKind.IMAGE, src="media/a.png", caption="A"),
            b"png-bytes",
        ).render()
        self.assertEqual(
            media.src,
            "data:image/png;base64," + base64.b64encode(b"png-bytes").decode("ascii"),
        )
        self.assertEqual(media.caption, "A")

    def test_video_file_is_embedded_as_video(self) -> None:
        media = MediaRenderer(
            MediaItem(kind=MediaKind.VIDEO_FILE, src="media/clip.mp4"), b"mp4"
        ).render()
        self.assertEqual(media.kind, RenderKind.VIDEO)
        self.assertTrue(media.src.startswith("data:video/mp4;base64,"))

    def test_unsupported_file_type_is_rejected(self) -> None:
        with self.assertRaises(DemoBuildError):
            MediaRenderer(
                MediaItem(kind=MediaKind.IMAGE, src="media/a.bmp"), b"x"
            ).render()


class TestBlurApplier(unittest.TestCase):
    def test_detail_inside_the_area_is_destroyed_and_outside_is_kept(self) -> None:
        image = Image.new("RGB", (400, 200), (255, 255, 255))
        for x in range(0, 200, 2):
            for y in range(0, 100):
                image.putpixel((x, y), (0, 0, 0))
        result = BlurApplier(image, [BlurArea(x=0, y=0, w=50, h=50)]).apply()
        inside = {result.getpixel((x, 50)) for x in range(40, 60)}
        self.assertLess(len(inside), 6)
        self.assertEqual(result.getpixel((300, 150)), (255, 255, 255))
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0))


class TestImageEncoder(unittest.TestCase):
    def test_full_resolution_is_kept_by_default(self) -> None:
        uri = ImageEncoder(
            Image.new("RGB", (4096, 100), (10, 20, 30)), BuildOptions()
        ).encode()
        decoded = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
        self.assertEqual(decoded.width, 4096)
        self.assertTrue(uri.startswith("data:image/webp;base64,"))

    def test_max_width_shrinks_and_jpeg_is_available(self) -> None:
        options = BuildOptions(max_width=1000, image_format=ImageFormat.JPEG)
        uri = ImageEncoder(Image.new("RGB", (4000, 100)), options).encode()
        decoded = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
        self.assertEqual(decoded.width, 1000)
        self.assertTrue(uri.startswith("data:image/jpeg;base64,"))


class TestPageBuilder(unittest.TestCase):
    def test_page_text_cannot_close_the_script_element(self) -> None:
        page = PageBuilder(
            TEMPLATE, _snapshot(), [_rendered("</script><b>x</b>")]
        ).build()
        self.assertNotIn("</script><b>", page)
        self.assertEqual(_payload(page)["steps"][0]["caption"], "</script><b>x</b>")

    def test_title_is_escaped_and_bad_accent_or_cta_fall_back(self) -> None:
        snapshot = _snapshot(
            title="A & B",
            accent="red;}",
            outro_title="Done",
            cta_label="Go",
            cta_url="javascript:alert(1)",
        )
        page = PageBuilder(TEMPLATE, snapshot, [_rendered("ok")]).build()
        payload = _payload(page)
        self.assertIn("<title>A &amp; B</title>", page)
        self.assertEqual(payload["accent"], DEFAULT_ACCENT)
        self.assertIsNone(payload["outro"]["cta_url"])

    def test_missing_placeholder_raises(self) -> None:
        with self.assertRaises(ValueError):
            PageBuilder("<html></html>", _snapshot(), [_rendered("ok")]).build()


class TestCheckSheetBuilder(unittest.TestCase):
    def test_hotspot_and_blur_outlines_are_drawn(self) -> None:
        image = Image.new("RGB", (2048, 1000), (255, 255, 255))
        steps = [
            _snapshot_step(1, Hotspot(x=10, y=10, w=20, h=20)),
            _snapshot_step(2, None, [BlurArea(x=50, y=50, w=20, h=20)]),
        ]
        sheet = CheckSheetBuilder([image, image], steps).build()
        self.assertEqual(sheet.width, CHECK_TILE_WIDTH * 2)
        self.assertEqual(
            sheet.getpixel((round(0.10 * CHECK_TILE_WIDTH) + 1, 51)), HOTSPOT_OUTLINE
        )
        self.assertEqual(
            sheet.getpixel(
                (CHECK_TILE_WIDTH + round(0.50 * CHECK_TILE_WIDTH) + 1, 251)
            ),
            BLUR_OUTLINE,
        )

    def test_mismatched_lengths_raise(self) -> None:
        with self.assertRaises(ValueError):
            CheckSheetBuilder([Image.new("RGB", (10, 10))], []).build()


if __name__ == "__main__":
    unittest.main()
