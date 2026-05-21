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
import re
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
from tip_generator import (
    parse_step_count, apply_priority_fixes, make_step_detail, _detail_differs_from_title,
    SLIDE_EMOJIS,
)

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
EMOJI_FONT = [
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
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
STEP_EMOJIS     = ["💡", "⚡", "🎯", "✅", "🚀"]
BG_STYLE_PRESETS = [
    ((5, 10, 30, 150), (5, 10, 30, 235)),
    ((45, 25, 10, 130), (25, 12, 5, 220)),
    ((10, 35, 50, 140), (5, 18, 35, 225)),
    ((30, 10, 40, 135), (15, 5, 25, 215)),
]

# Layout zones (9:16) — keeps caption off cards/dots
TOP_BAR_H       = 110
BOTTOM_STRIP_H  = 100
CAPTION_H       = 170
CONTENT_TOP     = 130
CONTENT_BOTTOM  = VIDEO_HEIGHT - BOTTOM_STRIP_H - CAPTION_H - 30
STEP_CIRCLE_CY  = CONTENT_TOP + 200   # fixed — not zone midpoint (avoids dead space)


# ── Helpers ────────────────────────────────────────────────────────────────────

_font_warned = False
_emoji_supported: Optional[bool] = None


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


def _content_zone_mid() -> int:
    return (CONTENT_TOP + CONTENT_BOTTOM) // 2


def _emoji_font_supported() -> bool:
    """True when a color-emoji font exists (macOS/Windows/Noto). Linux CI usually False."""
    global _emoji_supported
    if _emoji_supported is not None:
        return _emoji_supported
    _emoji_supported = any(os.path.exists(p) for p in EMOJI_FONT)
    return _emoji_supported


def _draw_accent_dot(d, cx: int, cy: int, radius: int, color: str) -> None:
    d.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=_hex_rgb(color),
    )


def _draw_bookmark_icon(d, cx: int, cy: int, height: int, color: str) -> None:
    """Simple bookmark shape when emoji fonts are unavailable."""
    w = max(int(height * 0.65), 12)
    h = height
    x0, y0 = cx - w // 2, cy - h // 2
    x1 = cx + w // 2
    notch = h // 4
    rgb = _hex_rgb(color)
    d.rectangle([x0, y0, x1, cy + h // 2 - notch], fill=rgb)
    d.polygon([(x0, cy + h // 2 - notch), (x1, cy + h // 2 - notch), (cx, y0 + h)], fill=rgb)


def _draw_centered_headline(d, W: int, y: int, headline: str, font,
                            max_w: int, emoji: str = "", accent: str = AMBER,
                            shadow: bool = True, spacing: int = 12) -> int:
    """Headline centered; accent dot instead of emoji when PIL fonts lack glyphs."""
    use_dot = bool(emoji) and not _emoji_font_supported()
    reserve = 36 if use_dot else 0
    if emoji and _emoji_font_supported():
        headline = f"{emoji}  {headline}"
    for i, line in enumerate(_wrap(d, headline, font, max_w - reserve)):
        lw = _text_w(d, line, font)
        tx = (W - lw) // 2
        if use_dot and i == 0:
            lh = _text_h(d, line, font)
            _draw_accent_dot(d, tx - 20, y + lh // 2, 10, accent)
        if shadow:
            d.text((tx + 2, y + 2), line, font=font, fill=(0, 0, 0))
        d.text((tx, y), line, font=font, fill=WHITE)
        y += _text_h(d, line, font) + spacing
    return y


def _draw_centered_pill(overlay, d, text: str, font, y: int, W: int,
                        fill, outline=None, pad_x: int = 24, pad_y: int = 10,
                        radius: int = 12, text_fill: str = WHITE) -> int:
    tw, th = _text_w(d, text, font), _text_h(d, text, font)
    pw, ph = tw + 2 * pad_x, th + 2 * pad_y
    x0 = (W - pw) // 2
    kw = {"outline": outline, "outline_w": 2} if outline else {}
    _draw_rounded_rect_rgba(overlay, (x0, y, x0 + pw, y + ph),
                            radius=radius, fill=fill, **kw)
    d.text((x0 + pad_x, y + pad_y), text, font=font, fill=text_fill)
    return y + ph


def _draw_wrapped_centered(d, text: str, font, max_w: int, W: int, y: int,
                           fill: str = WHITE, shadow: bool = False,
                           spacing: int = 10) -> int:
    for line in _wrap(d, text, font, max_w):
        lw = _text_w(d, line, font)
        tx = (W - lw) // 2
        if shadow:
            d.text((tx + 2, y + 2), line, font=font, fill=(0, 0, 0))
        d.text((tx, y), line, font=font, fill=fill)
        y += _text_h(d, line, font) + spacing
    return y


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


def _topic_to_query(topic: str, step_index: int = 0, kind: str = "step") -> str:
    """Build photo keywords — blend full topic with step so short titles still match."""
    stopwords = {
        "how", "to", "the", "a", "an", "in", "on", "at", "for", "of", "and", "or",
        "is", "are", "you", "your", "my", "i", "that", "this", "with", "without",
        "when", "why", "what", "can", "start", "using", "into", "from", "all",
        "top", "best", "tips", "ways", "most", "watch", "try", "today", "comment",
    }
    visual_boost = {
        "ai": "artificial intelligence laptop workspace",
        "freelance": "freelancer home office laptop money",
        "coding": "programmer coding screen office",
        "productivity": "productive desk planner coffee",
        "network": "business networking handshake office",
        "career": "office professional career growth",
        "learning": "student studying books laptop",
    }
    t_lower = topic.lower()
    boost = ""
    for key, phrase in visual_boost.items():
        if key in t_lower or (key == "ai" and re.search(r"\bai\b", t_lower)):
            boost = phrase
            break

    words = [w.lower().strip(",.?!") for w in topic.split()]
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    if kind == "hook" and boost:
        return boost
    if len(keywords) < 2 and boost:
        keywords = boost.split()[:4] + keywords
    elif boost and keywords:
        keywords = (boost.split()[:2] + keywords)[:4]

    if not keywords:
        return "productivity modern office"
    return " ".join(keywords[:4])


def _make_base_bg(photo: Optional[Image.Image], W: int, H: int,
                  bg_hex: str, style_idx: int = 0) -> Image.Image:
    """Photo (blurred, darkened) with per-slide tint/blur; gradient if fetch failed."""
    top_rgba, bot_rgba = BG_STYLE_PRESETS[style_idx % len(BG_STYLE_PRESETS)]
    if photo:
        bg = photo.copy().convert("RGBA").resize((W, H), Image.LANCZOS)
        blur = 3 + (style_idx % 3) * 2   # 3 / 5 / 7 px — rhythm without dropping photos
        bg = bg.filter(ImageFilter.GaussianBlur(radius=blur))
        scrim = _gradient_overlay((W, H), top_rgba=top_rgba, bot_rgba=bot_rgba)
        bg = Image.alpha_composite(bg, scrim)
        return bg.convert("RGBA")
    r, g, b = _hex_rgb(bg_hex)
    if style_idx % 3 == 1:
        r, g, b = min(r + 25, 255), min(g + 10, 255), b
    elif style_idx % 3 == 2:
        r, g, b = r, min(g + 15, 255), min(b + 20, 255)
    dr, dg, db = max(r - 35, 0), max(g - 35, 0), max(b - 35, 0)
    grad = _gradient_overlay((W, H), top_rgba=(r, g, b, 255), bot_rgba=(dr, dg, db, 255))
    overlay = _gradient_overlay((W, H), top_rgba=top_rgba, bot_rgba=bot_rgba)
    return Image.alpha_composite(grad.convert("RGBA"), overlay)


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

    def _normalize_step(self, step: Dict, index: int, total: int,
                        topic: str = "") -> Dict:
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
        if not _detail_differs_from_title(headline, detail):
            detail = make_step_detail(headline, topic, index)
        voice = (step.get("voice") or "").strip()
        if not voice:
            voice = f"{headline}. {detail}" if detail else headline
        cap = (step.get("caption") or "").strip()
        if cap.lower() == headline.lower() or cap.lower() == detail.lower():
            cap = ""
        emoji = (step.get("emoji") or "").strip()
        if not emoji:
            slide_emojis = step.get("_slide_emojis") or SLIDE_EMOJIS
            emoji = slide_emojis[(index + 1) % len(slide_emojis)] if slide_emojis else STEP_EMOJIS[index % len(STEP_EMOJIS)]
        show_why = _detail_differs_from_title(headline, detail)
        return {
            "headline": headline,
            "detail": detail,
            "voice": voice,
            "caption": cap,
            "emoji": emoji,
            "show_why": show_why,
        }

    def _sections_from_tip(self, tip: Dict) -> List[Dict]:
        topic = tip.get("queue_topic") or tip.get("tip_title", "")
        tip = apply_priority_fixes(tip, topic)
        n_steps = parse_step_count(topic, tip)
        durations = self._durations_for(n_steps)
        di = 0

        hook_title = tip.get("hook", "")
        hook_voice = tip.get("hook_voice") or hook_title
        hook_sub = tip.get("hook_subtitle", "") or f"Watch all {n_steps} tips below"
        slide_emojis = tip.get("slide_emojis") or SLIDE_EMOJIS

        steps = (tip.get("steps") or [])[:n_steps]
        while len(steps) < n_steps:
            steps.append({"title": f"Step {len(steps) + 1}", "detail": "", "voice": ""})

        step_sections_data = []
        for i, raw in enumerate(steps):
            norm = self._normalize_step(raw, i, n_steps, topic=topic)
            step_sections_data.append(norm)

        step_previews = [
            {"num": i + 1, "title": s["headline"][:42]}
            for i, s in enumerate(step_sections_data)
        ]
        tip1_teaser = step_sections_data[0]["headline"] if step_sections_data else ""

        sections = [{
            "kind":          "hook",
            "label":         "TODAY'S TIP",
            "title":         hook_title,
            "subtitle":      hook_sub,
            "caption":       "",
            "voice":         hook_voice,
            "duration":      durations[di],
            "num_steps":     n_steps,
            "step_previews": step_previews,
            "tip1_teaser":   tip1_teaser,
            "topic":         topic,
        }]
        di += 1

        for i, norm in enumerate(step_sections_data):
            sections.append({
                "kind":      "step",
                "step_num":  i + 1,
                "num_steps": n_steps,
                "label":     f"STEP {i + 1} / {n_steps}",
                "title":     norm["headline"],
                "detail":    norm["detail"],
                "caption":   norm["caption"],
                "voice":     norm["voice"],
                "emoji":     norm["emoji"],
                "show_why":  norm["show_why"],
                "duration":  durations[di],
                "color":     STEP_COLORS[i % len(STEP_COLORS)],
                "topic":     topic,
            })
            di += 1

        cta_line1 = tip.get("cta_line1", "")
        if not cta_line1 or cta_line1.strip().lower() in (
            "save this and try it today", "save this for later",
        ):
            short_topic = topic.strip().rstrip("?")[:50] if topic else "this"
            cta_line1 = f"Save these {n_steps} tips on {short_topic}"
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
            "topic":     topic,
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
                           current: int, total: int, accent: str,
                           label: str = ""):
        """Segmented progress bar with optional pill label above the segments."""
        gap = 14
        bar_h = 16
        if label:
            f_lbl = _font(FONT_BOLD, 26)
            pill_y = y - 50
            _draw_centered_pill(
                overlay, draw, label, f_lbl, pill_y, W,
                fill=(8, 16, 40, 200),
                outline=_hex_rgba(accent, 160),
                pad_x=18, pad_y=8, radius=10,
            )
        bar_w = W - 2 * margin
        seg_w = max(24, (bar_w - (total - 1) * gap) // total)
        x = (W - (total * seg_w + (total - 1) * gap)) // 2
        for i in range(total):
            filled = i < current
            fill = _hex_rgba(accent, 255 if filled else 80)
            if not filled:
                fill = (255, 255, 255, 70)
            _draw_rounded_rect_rgba(
                overlay, (x, y, x + seg_w, y + bar_h), radius=8, fill=fill,
            )
            x += seg_w + gap

    def _render_slide(self, section: Dict, photo: Optional[Image.Image],
                      sections: List[Dict]) -> Image.Image:
        W, H   = VIDEO_WIDTH, VIDEO_HEIGHT
        margin = 68
        max_w  = W - 2 * margin
        kind   = section.get("kind", "hook")

        slide_idx = section.get("step_num", 0) or 0
        if kind == "hook":
            slide_idx = 0
        elif kind == "cta":
            slide_idx = section.get("num_steps", 3) + 1
        base = _make_base_bg(photo, W, H, self.bg_hex, style_idx=slide_idx)
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
        td = ImageDraw.Draw(top_bar)
        chan_w = _text_w(td, CHANNEL_NAME, f_chan) + 32
        chan_x = margin
        _draw_rounded_rect_rgba(top_bar, (chan_x, 18, chan_x + chan_w, 82),
                                radius=12, fill=(8, 16, 40, 200),
                                outline=_hex_rgba(self.accent, 120), outline_w=2)
        td.text((chan_x + 16, 28), CHANNEL_NAME, font=f_chan, fill=WHITE)
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
        """Intro with teaser grid, swipe cue, and tip 1 preview."""
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        n = section.get("num_steps", 3)

        hero_top = CONTENT_TOP + 16
        hero_bot = CONTENT_BOTTOM - 36
        _draw_rounded_rect_rgba(overlay,
                                (margin, hero_top, W - margin, hero_bot),
                                radius=32,
                                fill=(255, 255, 255, 20),
                                outline=_hex_rgba(self.accent, 90), outline_w=2)

        label = section.get("label", "TODAY'S TIP")
        y = CONTENT_TOP + 60
        y = _draw_centered_pill(overlay, d, label, f_label, y, W,
                                fill=_hex_rgba(self.accent, 230)) + 20
        f_hero = _font(FONT_BOLD, 72)
        for line in _wrap(d, section.get("title", ""), f_hero, max_w - 60):
            lw = _text_w(d, line, f_hero)
            tx = (W - lw) // 2
            d.text((tx + 3, y + 3), line, font=f_hero, fill=(0, 0, 0))
            d.text((tx, y), line, font=f_hero, fill=WHITE)
            y += _text_h(d, line, f_hero) + 16

        sub = section.get("subtitle", "")
        if sub:
            y += 12
            f_teaser = _font(FONT_REG, 36)
            for line in _wrap(d, sub, f_teaser, max_w - 80):
                lw = _text_w(d, line, f_teaser)
                d.text(((W - lw) // 2, y), line, font=f_teaser, fill=AMBER)
                y += _text_h(d, line, f_teaser) + 10

        # Numbered teaser circles
        previews = section.get("step_previews") or []
        if previews:
            y += 28
            circle_r = 36
            total_w = n * (circle_r * 2 + 20) - 20
            start_x = (W - total_w) // 2 + circle_r
            f_circ = _font(FONT_BOLD, 32)
            for i, p in enumerate(previews):
                num = p.get("num", i + 1)
                cx = start_x + i * (circle_r * 2 + 20)
                col = STEP_COLORS[(num - 1) % len(STEP_COLORS)]
                _draw_rounded_rect_rgba(
                    overlay,
                    (cx - circle_r, y - circle_r, cx + circle_r, y + circle_r),
                    radius=circle_r, fill=_hex_rgba(col, 210),
                )
                ns = str(num)
                d.text(
                    (cx - _text_w(d, ns, f_circ) // 2, y - _text_h(d, ns, f_circ) // 2),
                    ns, font=f_circ, fill=WHITE,
                )
            y += circle_r + 36

        # Swipe prompt
        swipe = "👇 Swipe for all tips" if _emoji_font_supported() else "Swipe for all tips ▼"
        f_swipe = _font(FONT_BOLD, 34)
        sw = _text_w(d, swipe, f_swipe)
        d.text(((W - sw) // 2, y), swipe, font=f_swipe, fill=WHITE)
        y += 48
        arrow = "▼"
        f_arr = _font(FONT_BOLD, 40)
        aw = _text_w(d, arrow, f_arr)
        d.text(((W - aw) // 2, y), arrow, font=f_arr, fill=AMBER)
        y += 52

        # Tip 1 teaser
        tip1 = (section.get("tip1_teaser") or "").strip()
        if tip1:
            f_t1 = _font(FONT_BOLD, 30)
            tip_lines = _wrap(d, tip1, f_t1, max_w - 120)
            teaser_h = 52 + sum(_text_h(d, ln, f_t1) + 4 for ln in tip_lines)
            card_w = max_w - 80
            card_x0 = (W - card_w) // 2
            _draw_rounded_rect_rgba(
                overlay, (card_x0, y, card_x0 + card_w, y + teaser_h),
                radius=16, fill=(255, 255, 255, 28),
                outline=_hex_rgba(self.accent, 100), outline_w=2,
            )
            up_w = _text_w(d, "Up first:", f_small)
            d.text(((W - up_w) // 2, y + 12), "Up first:", font=f_small, fill=AMBER)
            ty = y + 40
            for line in tip_lines:
                lw = _text_w(d, line, f_t1)
                d.text(((W - lw) // 2, ty), line, font=f_t1, fill=WHITE)
                ty += _text_h(d, line, f_t1) + 4
            y += teaser_h + 24

        bar_y = CONTENT_BOTTOM - 58
        self._draw_progress_bar(
            d, overlay, W, bar_y, margin, 0, n, self.accent,
            label=f"{n} tips inside — swipe →",
        )

        return Image.alpha_composite(canvas, overlay), CONTENT_BOTTOM - 100

    # ── Step slide ─────────────────────────────────────────────────────────────

    def _render_step(self, canvas, section, margin, max_w, W, H,
                     f_label, f_big, f_body, f_num) -> Tuple[Image.Image, int]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        step_num = section.get("step_num", 1)
        n_steps  = section.get("num_steps", 3)
        col      = section.get("color", self.accent)
        emoji    = section.get("emoji", "💡")

        label = section.get("label", f"STEP {step_num} / {n_steps}")
        y = CONTENT_TOP + 12
        y = _draw_centered_pill(overlay, d, label, f_label, y, W,
                                fill=_hex_rgba(col, 220)) + 24

        cx, cy = W // 2, STEP_CIRCLE_CY
        r = 96
        f_num_big = _font(FONT_BOLD, 64)
        _draw_rounded_rect_rgba(overlay, (cx - r, cy - r, cx + r, cy + r),
                                radius=r, fill=_hex_rgba(col, 220))
        num = str(step_num)
        d.text(
            (cx - _text_w(d, num, f_num_big) // 2, cy - _text_h(d, num, f_num_big) // 2),
            num, font=f_num_big, fill=WHITE,
        )

        y = cy + r + 36
        headline = section.get("title", "")
        f_head = _font(FONT_BOLD, 58)
        y = _draw_centered_headline(
            d, W, y, headline, f_head, max_w - 40, emoji=emoji, accent=col,
        )

        detail = section.get("detail", "")
        show_why = section.get("show_why", True) and _detail_differs_from_title(headline, detail)
        bar_y = CONTENT_BOTTOM - 72

        if show_why and detail:
            card_y = y + 20
            card_bot = min(card_y + 240, CONTENT_BOTTOM - 130)
            _draw_rounded_rect_rgba(overlay,
                                    (margin + 16, card_y, W - margin - 16, card_bot),
                                    radius=24,
                                    fill=(255, 255, 255, 28),
                                    outline=_hex_rgba(col, 140), outline_w=2)
            f_why = _font(FONT_BOLD, 24)
            why_txt = "WHY IT MATTERS"
            if emoji and _emoji_font_supported():
                header = f"{emoji}  {why_txt}"
                hw = _text_w(d, header, f_why)
                d.text(((W - hw) // 2, card_y + 20), header, font=f_why, fill=AMBER)
            else:
                hw = _text_w(d, why_txt, f_why)
                hx = (W - hw) // 2
                hy = card_y + 20
                if emoji:
                    _draw_accent_dot(d, hx - 18, hy + _text_h(d, why_txt, f_why) // 2, 7, col)
                d.text((hx, hy), why_txt, font=f_why, fill=AMBER)
            dy = card_y + 64
            f_detail = _font(FONT_REG, 36)
            for line in _wrap(d, detail, f_detail, max_w - 80):
                lw = _text_w(d, line, f_detail)
                d.text(((W - lw) // 2, dy), line, font=f_detail, fill="#F1F5F9")
                dy += _text_h(d, line, f_detail) + 10
            bar_y = card_bot + 28

        self._draw_progress_bar(
            d, overlay, W, bar_y, margin, step_num, n_steps, col,
            label=f"Step {step_num} of {n_steps}",
        )

        return Image.alpha_composite(canvas, overlay), bar_y + 10

    # ── CTA slide ──────────────────────────────────────────────────────────────

    def _render_cta(self, canvas, section, all_sections, margin, max_w, W, H,
                    f_label, f_big, f_sub, f_body, f_num, f_small) -> Tuple[Image.Image, int]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        label = "SAVE THIS"
        y = CONTENT_TOP + 20
        y = _draw_centered_pill(overlay, d, label, f_label, y, W,
                                fill=_hex_rgba(self.accent, 220)) + 16

        if _emoji_font_supported():
            save_icon = "🔖"
            f_save = _font(FONT_BOLD, 56)
            sw = _text_w(d, save_icon, f_save)
            d.text(((W - sw) // 2, y), save_icon, font=f_save, fill=WHITE)
            y += _text_h(d, save_icon, f_save) + 8
        else:
            _draw_bookmark_icon(d, W // 2, y + 28, 52, WHITE)
            y += 60

        y = _draw_wrapped_centered(
            d, section.get("title", "Save this for later"), f_big,
            max_w - 40, W, y, fill=WHITE, shadow=True, spacing=16,
        ) + 8

        sub = section.get("subtitle", "")
        if sub:
            f_cta_sub = _font(FONT_BOLD, 34)
            for line in _wrap(d, sub, f_cta_sub, max_w - 40):
                lw = _text_w(d, line, f_cta_sub)
                fill = AMBER if "done" in line.lower() or "comment" in line.lower() else WHITE
                d.text(((W - lw) // 2, y), line, font=f_cta_sub, fill=fill)
                y += _text_h(d, line, f_cta_sub) + 12

        card_y = max(y + 32, _content_zone_mid() - 80)
        f_rec = _font(FONT_BOLD, 38)
        nf2 = _font(FONT_BOLD, 22)
        f_em = _font(FONT_BOLD, 34)
        draw_em = _emoji_font_supported()
        step_sections = [s for s in all_sections if s.get("kind") == "step"]
        recap_text_w = max_w - 120   # ~50+ chars at recap font size
        marker_r = 8
        marker_slot = marker_r * 2 + 12

        recap_rows: List[Tuple[List[str], int, str, str]] = []
        for s in step_sections:
            txt = (s.get("title") or "").strip()
            em = s.get("emoji", STEP_EMOJIS[len(recap_rows) % len(STEP_EMOJIS)])
            col = STEP_COLORS[len(recap_rows) % len(STEP_COLORS)]
            wrap_w = recap_text_w - (marker_slot if em and not draw_em else 0)
            lines = _wrap(d, txt, f_rec, wrap_w)
            line_step = _text_h(d, lines[0], f_rec) + 8
            recap_rows.append((lines, max(44, len(lines) * line_step), em, col))

        recap_body_h = sum(row_h for _, row_h, _, _ in recap_rows) + max(0, len(recap_rows) - 1) * 12
        card_bot = min(
            max(card_y + 78 + recap_body_h + 28, card_y + 220),
            CONTENT_BOTTOM - 40,
        )
        _draw_rounded_rect_rgba(overlay,
                                (margin, card_y, W - margin, card_bot),
                                radius=28,
                                fill=(255, 255, 255, 22),
                                outline=_hex_rgba(self.accent, 100), outline_w=2)

        recap_hdr = "Quick Recap"
        rhw = _text_w(d, recap_hdr, f_small)
        d.text(((W - rhw) // 2, card_y + 22), recap_hdr, font=f_small, fill=AMBER)
        div_w = max_w - 40
        div_x0 = (W - div_w) // 2
        _draw_rounded_rect_rgba(overlay,
                                (div_x0, card_y + 60, div_x0 + div_w, card_y + 63),
                                radius=2, fill=_hex_rgba(self.accent, 80))

        ry = card_y + 78
        for idx, (lines, row_h, em, col) in enumerate(recap_rows):
            num_s = str(idx + 1)
            badge_r = 18
            widest = max(_text_w(d, ln, f_rec) for ln in lines)
            row_parts_w = badge_r * 2 + 12 + widest
            if draw_em and em:
                row_parts_w += _text_w(d, em, f_em) + 12
            elif em:
                row_parts_w += marker_slot
            row_x = (W - row_parts_w) // 2
            cx_badge = row_x + badge_r
            badge_cy = ry + row_h // 2
            _draw_rounded_rect_rgba(overlay,
                                    (cx_badge - badge_r, badge_cy - badge_r,
                                     cx_badge + badge_r, badge_cy + badge_r),
                                    radius=badge_r, fill=_hex_rgba(col, 220))
            d.text(
                (cx_badge - _text_w(d, num_s, nf2) // 2,
                 badge_cy - _text_h(d, num_s, nf2) // 2),
                num_s, font=nf2, fill=WHITE,
            )
            ex = cx_badge + badge_r + 12
            if draw_em and em:
                d.text((ex, badge_cy - _text_h(d, em, f_em) // 2), em, font=f_em, fill=WHITE)
                ex += _text_w(d, em, f_em) + 12
            elif em:
                _draw_accent_dot(d, ex + marker_r, badge_cy, marker_r, col)
                ex += marker_slot
            ty = ry + max(0, (row_h - sum(_text_h(d, ln, f_rec) + 8 for ln in lines) + 8) // 2)
            for line in lines:
                d.text((ex, ty), line, font=f_rec, fill=WHITE)
                ty += _text_h(d, line, f_rec) + 8
            ry += row_h + 12

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
        tip = apply_priority_fixes(tip, topic)
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
                kind = sec.get("kind", "step")
                kw = _topic_to_query(
                    topic if kind == "hook" else f"{topic} {sec.get('title', '')}",
                    step_index=sec.get("step_num", i),
                    kind=kind,
                )
                print(f"[TipVideoBuilder] Slide {i + 1} ({kind}) background: '{kw}' ...")
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