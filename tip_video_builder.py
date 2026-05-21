"""
Build 9:16 tip Shorts — modern design with:
  - Unsplash photo backgrounds (topic-matched, no API key needed)
  - Glassmorphism frosted-glass cards
  - Full-bleed layout with gradient overlays
  - Ken Burns per-slide zoom
  - Fixed audio timing, caption compositing, and event-loop issues
"""
import asyncio
import io
import os
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, TTS_VOICE, QUEUE_OUTPUT_FOLDER,
    TIP_BRAND_COLOR, CHANNEL_NAME, CHANNEL_CTA, TIP_XFADE_DURATION,
    BACKGROUND_MUSIC_PATH, CHANNEL_LOGO_PATH, TIP_BG_COLOR, TIP_TEXT_COLOR,
    TIP_TOTAL_DURATION, TIP_FPS,
)
from tip_generator import parse_step_count, ensure_tip_steps

# ── Font paths ─────────────────────────────────────────────────────────────────
FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
FONT_EXTRA = [
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica Neue.ttf",
]

# ── Design tokens ──────────────────────────────────────────────────────────────
GLASS_BG        = (8, 20, 48, 200)      # semi-transparent dark navy (RGBA)
GLASS_BORDER    = (255, 140, 0, 100)    # amber border at low alpha
OVERLAY_DARK    = (5, 10, 30, 180)      # full-slide scrim
CAPTION_BG      = (0, 0, 0, 160)
AMBER           = "#FF8C00"
WHITE           = "#FFFFFF"
SLATE           = "#CBD5E1"
STEP_COLORS     = ["#FF8C00", "#FF6B35", "#FF4757", "#9B59B6", "#3498DB"]

# Layout zones (9:16) — keeps caption off cards/dots
TOP_BAR_H       = 110
BOTTOM_STRIP_H  = 100
CAPTION_H       = 170
CONTENT_TOP     = 130
CONTENT_BOTTOM  = VIDEO_HEIGHT - BOTTOM_STRIP_H - CAPTION_H - 30


# ── Helpers ────────────────────────────────────────────────────────────────────

_font_warned = False


def _font(paths: List[str], size: int) -> ImageFont.FreeTypeFont:
    global _font_warned
    for p in paths + FONT_EXTRA:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    for p in FONT_BOLD + FONT_REG:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    if not _font_warned:
        print("[TipVideoBuilder] Warning: no TTF fonts found — install DejaVu or Arial")
        _font_warned = True
    # Bitmap default is ~8px; scale via larger truetype on Linux if available
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_rgba(h: str, a: int = 255) -> Tuple[int, int, int, int]:
    r, g, b = _hex_rgb(h)
    return (r, g, b, a)


def _wrap(draw, text: str, font, max_w: int) -> List[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def _text_h(draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _text_w(draw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _draw_rounded_rect_rgba(img: Image.Image, xy: Tuple, radius: int,
                             fill=None, outline=None, outline_w: int = 3):
    """Draw a rounded rect with RGBA fill onto an RGBA image using paste."""
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if fill:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=fill)
    if outline:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius,
                             outline=outline, width=outline_w)
    img.paste(layer, (x0, y0), layer)


def _gradient_overlay(size: Tuple[int, int],
                       top_rgba=(0, 0, 0, 0),
                       bot_rgba=(0, 0, 0, 220)) -> Image.Image:
    """Vertical gradient RGBA image."""
    W, H = size
    grad = Image.new("RGBA", (W, H))
    for y in range(H):
        t = y / max(H - 1, 1)
        r = int(top_rgba[0] + (bot_rgba[0] - top_rgba[0]) * t)
        g = int(top_rgba[1] + (bot_rgba[1] - top_rgba[1]) * t)
        b = int(top_rgba[2] + (bot_rgba[2] - top_rgba[2]) * t)
        a = int(top_rgba[3] + (bot_rgba[3] - top_rgba[3]) * t)
        grad.paste((r, g, b, a), [0, y, W, y + 1])
    return grad


# ── Image fetching (free, no API key) ─────────────────────────────────────────

def _fetch_background_image(query: str, w: int = 1080, h: int = 1920,
                            slide_idx: int = 0) -> Optional[Image.Image]:
    """
    Topic-matched stock photo (Picsum seed + LoremFlickr keyword fallbacks).
    source.unsplash.com was retired; these work without an API key.
    """
    keywords = _topic_to_query(query)
    seed = abs(hash(f"{keywords}-{slide_idx}")) % 1_000_000
    tag_path = urllib.parse.quote(keywords.replace(" ", ","), safe=",")
    urls = [
        f"https://picsum.photos/seed/{seed}/{w}/{h}",
        f"https://loremflickr.com/{w}/{h}/{tag_path}",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TipVideoBuilder/1.0)"}
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            if len(data) < 5000:
                continue
            img = Image.open(io.BytesIO(data)).convert("RGB")
            return img.resize((w, h), Image.LANCZOS)
        except Exception:
            continue
    print(f"[TipVideoBuilder] Photo fetch failed for '{keywords}' — gradient bg")
    return None


def _topic_to_query(topic: str) -> str:
    """Extract 2-3 visual keywords from a topic string."""
    stopwords = {"how", "to", "the", "a", "an", "in", "on", "at", "for",
                 "of", "and", "or", "is", "are", "you", "your", "my", "i",
                 "that", "this", "with", "without", "when", "why", "what",
                 "5", "3", "10", "top", "best", "tips", "ways", "most"}
    words = [w.lower().strip(",.?!") for w in topic.split()]
    keywords = [w for w in words if w not in stopwords and len(w) > 2][:3]
    return " ".join(keywords) if keywords else "productivity office"


def _make_base_bg(photo: Optional[Image.Image], W: int, H: int,
                  bg_hex: str) -> Image.Image:
    """Photo (blurred, darkened) or gradient fallback — always W×H."""
    if photo:
        bg = photo.copy().convert("RGBA").resize((W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=4))
        # Dark scrim overlay — bottom heavier for readability
        scrim = _gradient_overlay((W, H),
                                  top_rgba=(5, 10, 30, 160),
                                  bot_rgba=(5, 10, 30, 230))
        bg = Image.alpha_composite(bg, scrim)
        return bg.convert("RGBA")
    else:
        # Gradient fallback
        r, g, b = _hex_rgb(bg_hex)
        dr, dg, db = max(r - 30, 0), max(g - 30, 0), max(b - 30, 0)
        grad = _gradient_overlay((W, H),
                                 top_rgba=(r, g, b, 255),
                                 bot_rgba=(dr, dg, db, 255))
        return grad


# ── Main builder ───────────────────────────────────────────────────────────────

class TipVideoBuilder:
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or TTS_VOICE
        self.bg_hex = TIP_BG_COLOR
        self.accent = AMBER
        self.xfade = TIP_XFADE_DURATION
        Path(QUEUE_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    def _total_duration_for(self, num_steps: int) -> float:
        """3 tips ≈ 28s; each extra tip adds ~3.5s so 5 tips fit comfortably."""
        if num_steps <= 3:
            return TIP_TOTAL_DURATION
        return TIP_TOTAL_DURATION + (num_steps - 3) * 3.5

    def _durations_for(self, num_steps: int) -> List[float]:
        """hook + N tip slides + save/CTA."""
        total = self._total_duration_for(num_steps)
        hook, cta = 4.0, 4.2
        budget = total - hook - cta
        per = round(budget / max(num_steps, 1), 2)
        return [hook] + [per] * num_steps + [cta]

    def _normalize_step(self, step: Dict, index: int, total: int) -> Dict:
        headline = (
            step.get("title") or step.get("caption")
            or step.get("line") or f"Step {index + 1}"
        ).strip()
        detail = (
            step.get("detail") or step.get("line")
            or step.get("subtitle") or ""
        ).strip()
        if not detail or detail.lower() == headline.lower():
            detail = step.get("body", "").strip()
        voice = (step.get("voice") or "").strip()
        if not voice:
            voice = f"{headline}. {detail}" if detail else headline
        cap = (step.get("caption") or "").strip()
        if cap.lower() == headline.lower() or cap.lower() == detail.lower():
            cap = ""
        return {
            "headline": headline,
            "detail": detail or headline,
            "voice": voice,
            "caption": cap,
        }

    def _sections_from_tip(self, tip: Dict) -> List[Dict]:
        topic = tip.get("queue_topic") or tip.get("tip_title", "")
        tip = ensure_tip_steps(tip, topic)
        n_steps = parse_step_count(topic, tip)
        durations = self._durations_for(n_steps)
        di = 0

        hook_title = tip.get("hook", "")
        hook_voice = tip.get("hook_voice") or hook_title
        hook_sub = tip.get("hook_subtitle", "") or f"Watch all {n_steps} tips below"

        sections = [{
            "kind":      "hook",
            "label":     "TODAY'S TIP",
            "title":     hook_title,
            "subtitle":  hook_sub,
            "caption":   "",
            "voice":     hook_voice,
            "duration":  durations[di],
            "num_steps": n_steps,
        }]
        di += 1

        steps = (tip.get("steps") or [])[:n_steps]
        while len(steps) < n_steps:
            steps.append({"title": f"Step {len(steps) + 1}", "detail": "", "voice": ""})

        for i, raw in enumerate(steps):
            norm = self._normalize_step(raw, i, n_steps)
            sections.append({
                "kind":      "step",
                "step_num":  i + 1,
                "num_steps": n_steps,
                "label":     f"STEP {i + 1} / {n_steps}",
                "title":     norm["headline"],
                "detail":    norm["detail"],
                "caption":   norm["caption"],
                "voice":     norm["voice"],
                "duration":  durations[di],
                "color":     STEP_COLORS[i % len(STEP_COLORS)],
            })
            di += 1

        cta_line1 = tip.get("cta_line1", "Save this for later")
        cta_line2 = tip.get("cta_line2", "Comment 'DONE' when you try it!")
        cta_voice = tip.get("cta_voice") or f"{cta_line1}. {cta_line2}"
        sections.append({
            "kind":      "cta",
            "label":     "SAVE THIS",
            "title":     cta_line1,
            "subtitle":  cta_line2,
            "caption":   "",
            "voice":     cta_voice,
            "duration":  durations[di],
            "num_steps": n_steps,
        })
        return sections

    # ── Slide renderer ─────────────────────────────────────────────────────────

    def _paste_channel_logo(self, canvas: Image.Image, W: int, margin: int) -> Image.Image:
        """Brand logo on every slide (logo.png or CHANNEL_LOGO_PATH)."""
        if not CHANNEL_LOGO_PATH or not os.path.isfile(CHANNEL_LOGO_PATH):
            return canvas
        try:
            logo = Image.open(CHANNEL_LOGO_PATH).convert("RGBA")
            size = 88
            logo.thumbnail((size, size), Image.LANCZOS)
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            x = W - margin - size - 8
            y = 16
            _draw_rounded_rect_rgba(
                layer, (x - 8, y - 6, x + size + 8, y + size + 6),
                radius=14, fill=(255, 255, 255, 35),
                outline=_hex_rgba(self.accent, 100), outline_w=2,
            )
            layer.paste(logo, (x, y), logo)
            return Image.alpha_composite(canvas, layer)
        except Exception as e:
            print(f"[TipVideoBuilder] Logo skip: {e}")
            return canvas

    def _draw_progress_bar(self, draw, overlay, W: int, y: int, margin: int,
                           current: int, total: int, accent: str):
        """Segmented progress bar (no slide counter text)."""
        bar_w = W - 2 * margin
        seg_w = (bar_w - (total - 1) * 8) // total
        x = margin
        for i in range(total):
            fill = _hex_rgba(accent, 220) if i < current else (255, 255, 255, 50)
            _draw_rounded_rect_rgba(overlay, (x, y, x + seg_w, y + 10), radius=5, fill=fill)
            x += seg_w + 8

    def _render_slide(self, section: Dict, photo: Optional[Image.Image],
                      sections: List[Dict]) -> Image.Image:
        W, H   = VIDEO_WIDTH, VIDEO_HEIGHT
        margin = 68
        max_w  = W - 2 * margin
        kind   = section.get("kind", "hook")

        # Base background (RGBA)
        base = _make_base_bg(photo, W, H, self.bg_hex)
        if base.mode != "RGBA":
            base = base.convert("RGBA")

        canvas = base.copy()

        # Fonts
        f_chan  = _font(FONT_BOLD, 28)
        f_label = _font(FONT_BOLD, 30)
        f_big   = _font(FONT_BOLD, 72)
        f_med   = _font(FONT_BOLD, 52)
        f_sub   = _font(FONT_REG,  42)
        f_body  = _font(FONT_REG,  38)
        f_cap   = _font(FONT_BOLD, 34)
        f_cta   = _font(FONT_REG,  30)
        f_num   = _font(FONT_BOLD, 44)
        f_small = _font(FONT_BOLD, 26)

        canvas = canvas.resize((W, H), Image.LANCZOS).convert("RGBA")

        top_bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _draw_rounded_rect_rgba(top_bar, (margin, 18, margin + 200, 82),
                                radius=12, fill=(255, 255, 255, 25),
                                outline=(255, 255, 255, 50))
        td = ImageDraw.Draw(top_bar)
        td.text((margin + 16, 28), CHANNEL_NAME, font=f_chan, fill=WHITE)
        canvas = Image.alpha_composite(canvas, top_bar.convert("RGBA"))
        canvas = self._paste_channel_logo(canvas, W, margin)

        # ── Kind-specific content ──────────────────────────────────────────────
        content_bottom = CONTENT_BOTTOM

        if kind == "hook":
            canvas, content_bottom = self._render_hook(
                canvas, section, margin, max_w, W, H,
                f_label, f_big, f_sub, f_small,
            )
        elif kind == "step":
            canvas, content_bottom = self._render_step(
                canvas, section, margin, max_w, W, H,
                f_label, f_big, f_body, f_num,
            )
        elif kind == "cta":
            canvas, content_bottom = self._render_cta(
                canvas, section, sections, margin, max_w, W, H,
                f_label, f_big, f_sub, f_body, f_num, f_small,
            )

        cap = (section.get("caption") or "").strip()
        if cap:
            canvas = self._render_caption(
                canvas, cap, W, H, margin, f_cap, content_bottom,
            )

        # ── Bottom CTA strip ───────────────────────────────────────────────────
        strip = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _draw_rounded_rect_rgba(strip, (margin, H - 92, W - margin, H - 18),
                                radius=12, fill=(255, 255, 255, 18),
                                outline=_hex_rgba(self.accent, 80))
        sd = ImageDraw.Draw(strip)
        cw = _text_w(sd, CHANNEL_CTA, f_cta)
        sd.text(((W - cw) // 2, H - 72), CHANNEL_CTA, font=f_cta, fill=AMBER)
        canvas = Image.alpha_composite(canvas, strip)

        return canvas.convert("RGB")

    # ── Hook slide ─────────────────────────────────────────────────────────────

    def _render_hook(self, canvas, section, margin, max_w, W, H,
                     f_label, f_big, f_sub, f_small) -> Tuple[Image.Image, int]:
        """Intro only — no step spoilers."""
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        n = section.get("num_steps", 3)

        hero_top = CONTENT_TOP + 40
        _draw_rounded_rect_rgba(overlay,
                                (margin, hero_top, W - margin, CONTENT_BOTTOM - 40),
                                radius=32,
                                fill=(255, 255, 255, 20),
                                outline=_hex_rgba(self.accent, 90), outline_w=2)

        label = section.get("label", "TODAY'S TIP")
        _draw_rounded_rect_rgba(overlay,
                                (margin + 32, hero_top + 28, margin + 32 + 300, hero_top + 80),
                                radius=12, fill=_hex_rgba(self.accent, 230))
        d.text((margin + 52, hero_top + 38), label, font=f_label, fill=WHITE)

        y = hero_top + 110
        f_hero = _font(FONT_BOLD, 78)
        for line in _wrap(d, section.get("title", ""), f_hero, max_w - 60):
            lw = _text_w(d, line, f_hero)
            tx = (W - lw) // 2
            d.text((tx + 3, y + 3), line, font=f_hero, fill=(0, 0, 0))
            d.text((tx, y), line, font=f_hero, fill=WHITE)
            y += _text_h(d, line, f_hero) + 20

        sub = section.get("subtitle", "")
        if sub:
            y += 24
            f_teaser = _font(FONT_REG, 40)
            for line in _wrap(d, sub, f_teaser, max_w - 80):
                lw = _text_w(d, line, f_teaser)
                d.text(((W - lw) // 2, y), line, font=f_teaser, fill=AMBER)
                y += _text_h(d, line, f_teaser) + 12

        bar_y = CONTENT_BOTTOM - 70
        self._draw_progress_bar(d, overlay, W, bar_y, margin, 0, n, self.accent)
        d.text((margin, bar_y + 22), "Swipe through each tip", font=f_small, fill=SLATE)

        return Image.alpha_composite(canvas, overlay), CONTENT_BOTTOM - 120

    # ── Step slide ─────────────────────────────────────────────────────────────

    def _render_step(self, canvas, section, margin, max_w, W, H,
                     f_label, f_big, f_body, f_num) -> Tuple[Image.Image, int]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        step_num = section.get("step_num", 1)
        n_steps  = section.get("num_steps", 3)
        col      = section.get("color", self.accent)

        _draw_rounded_rect_rgba(overlay, (margin, CONTENT_TOP, margin + 10, CONTENT_TOP + 480),
                                radius=5, fill=_hex_rgba(col, 230))

        label = section.get("label", f"STEP {step_num} / {n_steps}")
        _draw_rounded_rect_rgba(overlay,
                                (margin + 28, CONTENT_TOP + 8, margin + 28 + 320, CONTENT_TOP + 60),
                                radius=10, fill=_hex_rgba(col, 220))
        d.text((margin + 48, CONTENT_TOP + 16), label, font=f_label, fill=WHITE)

        cx, cy = W // 2, CONTENT_TOP + 200
        r = 72
        _draw_rounded_rect_rgba(overlay, (cx - r, cy - r, cx + r, cy + r),
                                radius=r, fill=_hex_rgba(col, 200))
        num = str(step_num)
        d.text((cx - _text_w(d, num, f_num) // 2, cy - _text_h(d, num, f_num) // 2),
               num, font=f_num, fill=WHITE)

        y = cy + r + 48
        headline = section.get("title", "")
        f_head = _font(FONT_BOLD, 64)
        for line in _wrap(d, headline, f_head, max_w - 50):
            lw = _text_w(d, line, f_head)
            tx = (W - lw) // 2
            d.text((tx + 2, y + 2), line, font=f_head, fill=(0, 0, 0))
            d.text((tx, y), line, font=f_head, fill=WHITE)
            y += _text_h(d, line, f_head) + 14

        card_y = y + 32
        card_bot = min(card_y + 280, CONTENT_BOTTOM - 100)
        _draw_rounded_rect_rgba(overlay,
                                (margin + 16, card_y, W - margin - 16, card_bot),
                                radius=24,
                                fill=(255, 255, 255, 24),
                                outline=_hex_rgba(col, 120), outline_w=2)

        d.text((margin + 36, card_y + 20), "WHY IT MATTERS", font=_font(FONT_BOLD, 24), fill=AMBER)
        detail = section.get("detail", "")
        dy = card_y + 58
        for line in _wrap(d, detail, f_body, max_w - 80):
            lw = _text_w(d, line, f_body)
            d.text(((W - lw) // 2, dy), line, font=f_body, fill="#E2E8F0")
            dy += _text_h(d, line, f_body) + 12

        bar_y = card_bot + 36
        self._draw_progress_bar(d, overlay, W, bar_y, margin, step_num, n_steps, col)

        return Image.alpha_composite(canvas, overlay), bar_y + 20

    # ── CTA slide ──────────────────────────────────────────────────────────────

    def _render_cta(self, canvas, section, all_sections, margin, max_w, W, H,
                    f_label, f_big, f_sub, f_body, f_num, f_small) -> Tuple[Image.Image, int]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        # Accent bar
        _draw_rounded_rect_rgba(overlay, (margin, 140, margin + 10, 620),
                                radius=5, fill=_hex_rgba(self.accent, 230))

        label = "SAVE THIS"
        _draw_rounded_rect_rgba(overlay, (margin + 30, 148, margin + 30 + 240, 200),
                                radius=10, fill=_hex_rgba(self.accent, 220))
        d.text((margin + 50, 156), label, font=f_label, fill=WHITE)

        f_label2 = _font(FONT_BOLD, 30)

        y = 232
        title_lines = _wrap(d, section.get("title", "Save this for later"), f_big, max_w - 40)
        for line in title_lines:
            d.text((margin + 30 + 2, y + 2), line, font=f_big, fill=(0, 0, 0))
            d.text((margin + 30, y), line, font=f_big, fill=WHITE)
            y += _text_h(d, line, f_big) + 16

        sub = section.get("subtitle", "")
        if sub:
            y += 20
            for line in _wrap(d, sub, f_sub, max_w - 40):
                lw = _text_w(d, line, f_sub)
                d.text((margin + 30, y), line, font=f_sub, fill=SLATE)
                y += _text_h(d, line, f_sub) + 10

        card_y   = max(y + 44, 660)
        card_bot = min(card_y + 360, CONTENT_BOTTOM - 40)
        _draw_rounded_rect_rgba(overlay,
                                (margin, card_y, W - margin, card_bot),
                                radius=28,
                                fill=(255, 255, 255, 22),
                                outline=_hex_rgba(self.accent, 100), outline_w=2)

        # Header inside card
        d.text((margin + 28, card_y + 22), "Quick Recap", font=f_small, fill=AMBER)
        _draw_rounded_rect_rgba(overlay,
                                (margin + 20, card_y + 60,
                                 W - margin - 20, card_y + 63),
                                radius=2, fill=_hex_rgba(self.accent, 80))

        ry = card_y + 78
        f_rec = _font(FONT_BOLD, 32)
        step_sections = [s for s in all_sections if s.get("kind") == "step"]
        for idx, s in enumerate(step_sections):
            col = STEP_COLORS[idx % len(STEP_COLORS)]
            txt = s.get("title", "")
            if len(txt) > 36:
                txt = txt[:34] + "…"
            # Bullet circle
            _draw_rounded_rect_rgba(overlay,
                                    (margin + 28, ry + 4, margin + 54, ry + 30),
                                    radius=14, fill=_hex_rgba(col, 200))
            dn = ImageDraw.Draw(overlay)
            nf2 = _font(FONT_BOLD, 20)
            dn.text((margin + 33, ry + 6), str(idx + 1), font=nf2, fill=WHITE)
            d.text((margin + 70, ry), txt, font=f_rec, fill=WHITE)
            ry += 102

        return Image.alpha_composite(canvas, overlay), card_bot

    # ── Caption ────────────────────────────────────────────────────────────────

    def _render_caption(self, canvas: Image.Image, cap: str,
                        W: int, H: int, margin: int, f_cap,
                        content_bottom: int) -> Image.Image:
        """Burned-in caption with proper RGBA compositing (no overlap with cards)."""
        cap_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cap_h = CAPTION_H
        cap_y = max(content_bottom + 24, H - BOTTOM_STRIP_H - cap_h - 24)
        cap_y = min(cap_y, H - BOTTOM_STRIP_H - cap_h - 12)

        _draw_rounded_rect_rgba(cap_layer,
                                (margin - 16, cap_y,
                                 W - margin + 16, cap_y + cap_h),
                                radius=18,
                                fill=CAPTION_BG)

        d = ImageDraw.Draw(cap_layer)
        lines = []
        for part in cap.split("\n"):
            part = part.strip()
            if part:
                lines.extend(_wrap(d, part, f_cap, W - 2 * margin - 20))

        y = cap_y + 16
        for line in lines:
            lw = _text_w(d, line, f_cap)
            tx = (W - lw) // 2
            d.text((tx + 2, y + 2), line, font=f_cap, fill=(0, 0, 0))
            d.text((tx, y), line, font=f_cap, fill=WHITE)
            y += _text_h(d, line, f_cap) + 10

        return Image.alpha_composite(canvas, cap_layer)

    # ── TTS helpers ────────────────────────────────────────────────────────────

    def _run_tts(self, text: str, path: str) -> bool:
        """Run TTS safely when an event loop may already be running."""
        import concurrent.futures
        import edge_tts

        async def _do():
            comm = edge_tts.Communicate(text.strip(), self.voice, rate="+5%")
            await comm.save(path)

        def _sync():
            asyncio.run(_do())

        try:
            asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(_sync).result()
        except RuntimeError:
            _sync()

        return os.path.exists(path) and os.path.getsize(path) > 100

    def _probe_duration(self, path: str) -> float:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True,
        )
        try:
            return float(r.stdout.strip())
        except ValueError:
            return 0.0

    def _atempo_chain(self, factor: float) -> str:
        """Build atempo filter chain; each atempo must stay in [0.5, 2.0]."""
        filters = []
        t = factor
        while t < 0.5:
            filters.append("atempo=0.5")
            t /= 0.5
        while t > 2.0:
            filters.append("atempo=2.0")
            t /= 2.0
        filters.append(f"atempo={max(0.5, min(2.0, t)):.4f}")
        return ",".join(filters)

    def _fit_audio_to_duration(self, src: str, dst: str, target: float) -> bool:
        """Stretch/trim audio to exactly `target` seconds with safe atempo range."""
        dur = self._probe_duration(src)
        if dur <= 0:
            return False

        if abs(dur - target) < 0.06:
            af = f"apad=pad_dur={max(0, target - dur):.3f},atrim=0:{target:.3f}"
        elif dur > target:
            speed = dur / target
            if speed <= 2.0:
                af = f"{self._atempo_chain(speed)},atrim=0:{target:.3f}"
            else:
                af = f"atrim=0:{target:.3f}"
        else:
            stretch = dur / target
            af = (
                f"{self._atempo_chain(stretch)},"
                f"apad=pad_dur={max(0.05, target - dur / max(stretch, 0.01)):.3f},"
                f"atrim=0:{target:.3f}"
            )

        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-af", af, "-t", f"{target:.3f}",
            "-c:a", "libmp3lame", "-q:a", "4", dst,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[TipVideoBuilder] Audio fit: {r.stderr[-200:]}")
        return r.returncode == 0 and os.path.exists(dst)

    def _image_to_segment(self, png: str, duration: float, seg_path: str) -> bool:
        fps    = TIP_FPS
        frames = max(int(duration * fps), 2)
        z_expr = "1.04-0.04*on/(max(on-1\\,1))"
        vf = (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", png,
            "-vf", vf, "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-an", seg_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[TipVideoBuilder] Segment error: {result.stderr[-400:]}")
        return result.returncode == 0

    def _concat_video_xfade(self, segments: List[str], durations: List[float], out: str) -> bool:
        if len(segments) == 1:
            shutil.copy(segments[0], out)
            return True

        xfade = self.xfade
        inputs = []
        for seg in segments:
            inputs.extend(["-i", seg])

        if len(segments) == 2:
            offset = max(durations[0] - xfade, 0.1)
            fc = (f"[0:v][1:v]xfade=transition=fade:"
                  f"duration={xfade}:offset={offset:.3f}[vout]")
        else:
            parts = []
            offset = max(durations[0] - xfade, 0.1)
            parts.append(
                f"[0:v][1:v]xfade=transition=fade:duration={xfade}"
                f":offset={offset:.3f}[v01]"
            )
            prev, accumulated = "v01", durations[0] + durations[1] - xfade
            for i in range(2, len(segments)):
                offset = max(accumulated - xfade, 0.1)
                label  = "vout" if i == len(segments) - 1 else f"v{i:02d}"
                parts.append(
                    f"[{prev}][{i}:v]xfade=transition=fade:duration={xfade}"
                    f":offset={offset:.3f}[{label}]"
                )
                prev = label
                accumulated += durations[i] - xfade
            fc = ";".join(parts)

        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", fc, "-map", "[vout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TIP_FPS), out,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("[TipVideoBuilder] xfade failed — concat fallback")
            lst = os.path.join(os.path.dirname(out), "vconcat.txt")
            with open(lst, "w") as f:
                for s in segments:
                    f.write(f"file '{s}'\n")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                 "-c", "copy", out],
                capture_output=True,
            )
        return os.path.exists(out)

    def _merge_audio(self, paths: List[str], work: str) -> str:
        out = os.path.join(work, "voice_full.mp3")
        lst = os.path.join(work, "aconcat.txt")
        with open(lst, "w") as f:
            for p in paths:
                f.write(f"file '{p}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-c", "copy", out],
            capture_output=True,
        )
        return out if os.path.exists(out) else paths[0]

    def _final_mux(self, video: str, voice: str, output: str,
                   target_duration: Optional[float] = None) -> bool:
        bgm = BACKGROUND_MUSIC_PATH
        t   = target_duration if target_duration else TIP_TOTAL_DURATION
        if bgm and os.path.exists(bgm):
            fc = (
                "[1:a]volume=1.0[v];[2:a]volume=0.08,aloop=loop=-1:size=2e+09[m];"
                "[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]"
            )
            cmd = [
                "ffmpeg", "-y", "-i", video, "-i", voice, "-i", bgm,
                "-filter_complex", fc,
                "-map", "0:v:0", "-map", "[a]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TIP_FPS),
                "-c:a", "aac", "-b:a", "192k",
                "-t", f"{t:.3f}", "-movflags", "+faststart", output,
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-i", video, "-i", voice,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TIP_FPS),
                "-c:a", "aac", "-b:a", "192k",
                "-t", f"{t:.3f}", "-movflags", "+faststart", output,
            ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[TipVideoBuilder] Mux error: {r.stderr[-300:]}")
        return r.returncode == 0 and os.path.exists(output)

    # ── Public entry-point ─────────────────────────────────────────────────────

    def build(self, tip: Dict, output_path: Optional[str] = None) -> Optional[str]:
        sections = self._sections_from_tip(tip)
        n_tips = sum(1 for s in sections if s.get("kind") == "step")
        target_dur = self._total_duration_for(n_tips)
        print(
            f"[TipVideoBuilder] Slides: 1 topic + {n_tips} tips + 1 save "
            f"= {len(sections)} total (~{target_dur:.0f}s)"
        )
        if CHANNEL_LOGO_PATH:
            print(f"[TipVideoBuilder] Logo: {CHANNEL_LOGO_PATH}")
        else:
            print("[TipVideoBuilder] Logo: none (add logo.png in project root)")

        if output_path is None:
            from datetime import date
            output_path = os.path.join(
                QUEUE_OUTPUT_FOLDER,
                f"tip_{tip.get('generated_on', date.today().isoformat())}.mp4",
            )

        topic = tip.get("queue_topic") or tip.get("tip_title", "productivity")
        print(f"[TipVideoBuilder] Topic: {topic}")

        work = tempfile.mkdtemp(prefix="tip_build_")
        try:
            fitted_audio = []
            for i, sec in enumerate(sections):
                raw    = os.path.join(work, f"voice_raw_{i}.mp3")
                fitted = os.path.join(work, f"voice_fit_{i}.mp3")
                vtext  = (sec.get("voice") or sec.get("caption") or "").strip()
                if not vtext:
                    vtext = sec.get("title", "Tip")
                ok = self._run_tts(vtext, raw)
                if not ok:
                    print(f"[TipVideoBuilder] TTS failed for slide {i}")
                    return None
                if not self._fit_audio_to_duration(raw, fitted, sec["duration"]):
                    print(f"[TipVideoBuilder] Audio fit failed for slide {i}")
                    return None
                fitted_audio.append(fitted)

            seg_paths, durations = [], []
            for i, sec in enumerate(sections):
                kw = _topic_to_query(sec.get("title") or topic)
                print(f"[TipVideoBuilder] Slide {i + 1} background: '{kw}' ...")
                photo = _fetch_background_image(kw, slide_idx=i)
                slide = self._render_slide(sec, photo, sections)
                png = os.path.join(work, f"slide_{i}.png")
                slide.save(png, quality=95)
                dur = sec["duration"]
                seg = os.path.join(work, f"seg_{i}.mp4")
                if not self._image_to_segment(png, dur, seg):
                    print(f"[TipVideoBuilder] Segment failed for slide {i}")
                    return None
                seg_paths.append(seg)
                durations.append(dur)

            # Assemble
            video_only = os.path.join(work, "video_xfade.mp4")
            if not self._concat_video_xfade(seg_paths, durations, video_only):
                return None

            voice_full = self._merge_audio(fitted_audio, work)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            if not self._final_mux(video_only, voice_full, output_path,
                                   target_duration=target_dur):
                return None

            exact = os.path.join(work, "exact.mp4")
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", output_path,
                    "-vf", f"tpad=stop_mode=clone:stop_duration={max(0, target_dur)}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TIP_FPS),
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{target_dur:.3f}",
                    "-movflags", "+faststart", exact,
                ],
                capture_output=True,
            )
            if os.path.exists(exact):
                shutil.move(exact, output_path)

            actual = self._probe_duration(output_path)
            mb     = os.path.getsize(output_path) / (1024 * 1024)
            print(
                f"[TipVideoBuilder] ✅  {output_path}  "
                f"({mb:.1f} MB, {actual:.2f}s / target {target_dur:.1f}s)"
            )
            return output_path

        finally:
            shutil.rmtree(work, ignore_errors=True)