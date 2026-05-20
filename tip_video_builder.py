"""
Build 9:16 tip Shorts — fixed 28s timing, branded slides, burned-in captions, TTS.
Fixes: emoji rendering (PIL can't render Unicode emoji on Linux → replaced with drawn icons),
       empty slide space (rich visual layout with cards, decorators, body content),
       duplicate guard (topic hash check before generation).
"""
import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, TTS_VOICE, QUEUE_OUTPUT_FOLDER,
    TIP_BRAND_COLOR, CHANNEL_NAME, CHANNEL_CTA, TIP_XFADE_DURATION,
    BACKGROUND_MUSIC_PATH, CHANNEL_LOGO_PATH, TIP_BG_COLOR, TIP_TEXT_COLOR,
    TIP_SLIDE_DURATIONS, TIP_TOTAL_DURATION, TIP_FPS,
)

# ── Font paths (bold + regular, cross-platform) ──────────────────────────────
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
    "C:/Windows/Fonts/arial.ttf",
]

# Icon labels replacing emoji (PIL-renderable ASCII/Latin text)
STEP_ICON_LABELS = ["01", "02", "03"]
SLIDE_ICON_LABELS = ["HOOK", "STEP", "STEP", "STEP", "SAVE"]

# Colour for step-card background strips
CARD_BG = (10, 40, 80)          # slightly lighter than main bg
ACCENT_LIGHT = (255, 165, 50)   # warm amber
DIVIDER = (255, 140, 0, 80)     # translucent amber


# ── Helpers ───────────────────────────────────────────────────────────────────

def _font(paths: List[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> List[str]:
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


def _text_h(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _solid_bg(color: str) -> Image.Image:
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), _hex_rgb(color))
    return img


def _gradient_bg(top_hex: str, bottom_hex: str) -> Image.Image:
    """Vertical gradient background."""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    top = _hex_rgb(top_hex)
    bot = _hex_rgb(bottom_hex)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(VIDEO_WIDTH):
            img.putpixel((x, y), (r, g, b))
    return img


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int, int, int],
    radius: int,
    fill=None,
    outline=None,
    width: int = 2,
):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_icon_circle(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int, r: int,
    label: str, accent: str,
    font,
):
    """Draw a filled circle with a text label — replaces emoji."""
    acc = _hex_rgb(accent)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=acc)
    tw = _text_w(draw, label, font)
    th = _text_h(draw, label, font)
    draw.text((cx - tw // 2, cy - th // 2 - 2), label, font=font, fill="#FFFFFF")


def _draw_decorative_dots(draw: ImageDraw.ImageDraw, y: int, accent: str):
    """Small dot row as visual separator."""
    acc = _hex_rgb(accent)
    for i in range(5):
        x = VIDEO_WIDTH // 2 - 40 + i * 20
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=acc + (180,) if len(acc) == 3 else acc)


def _draw_horizontal_rule(
    draw: ImageDraw.ImageDraw, y: int, margin: int, accent: str, alpha: int = 120
):
    col = _hex_rgb(accent)
    draw.rectangle([(margin, y), (VIDEO_WIDTH - margin, y + 3)], fill=col)


# ── Main builder class ────────────────────────────────────────────────────────

class TipVideoBuilder:
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or TTS_VOICE
        self.bg_top = TIP_BG_COLOR          # dark navy
        self.bg_bot = "#061428"             # slightly darker
        self.accent = TIP_BRAND_COLOR       # amber
        self.text_color = TIP_TEXT_COLOR    # white
        self.slide_durations = list(TIP_SLIDE_DURATIONS)
        self.xfade = TIP_XFADE_DURATION
        Path(QUEUE_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    # ── Section builder ───────────────────────────────────────────────────────

    def _sections_from_tip(self, tip: Dict) -> List[Dict]:
        """Five slides: hook + 3 steps + CTA."""
        hook_caption = tip.get("hook", "")
        hook_voice   = tip.get("hook_voice") or hook_caption
        hook_subtitle = tip.get("hook_subtitle", "")

        sections = [{
            "kind":     "hook",
            "label":    "TODAY'S TIP",
            "title":    hook_caption,
            "subtitle": hook_subtitle,
            "caption":  hook_caption,
            "voice":    hook_voice,
            "duration": self.slide_durations[0],
        }]

        steps = tip.get("steps") or []
        for i in range(3):
            if i < len(steps):
                step = steps[i]
                cap  = step.get("caption") or step.get("line") or step.get("title", "")
                voice = step.get("voice") or cap
                title = step.get("title") or cap
            else:
                lines = tip.get("on_screen_lines") or []
                cap   = lines[i] if i < len(lines) else f"Step {i + 1}"
                voice = cap
                title = cap
            sections.append({
                "kind":     "step",
                "step_num": i + 1,
                "label":    f"STEP {i + 1}",
                "title":    cap,
                "subtitle": title if title != cap else "",
                "caption":  cap,
                "voice":    voice,
                "duration": self.slide_durations[i + 1],
            })

        cta_line1 = tip.get("cta_line1", "Save this for later")
        cta_line2 = tip.get("cta_line2", "Comment 'DONE' when you try it!")
        cta_voice = tip.get("cta_voice") or f"{cta_line1}. {cta_line2}"

        sections.append({
            "kind":     "cta",
            "label":    "ACTION",
            "title":    cta_line1,
            "subtitle": cta_line2,
            "caption":  f"{cta_line1}\n{cta_line2}",
            "voice":    cta_voice,
            "duration": self.slide_durations[4],
        })
        return sections

    # ── Slide renderer ────────────────────────────────────────────────────────

    def _render_slide(self, section: Dict, progress: str, total_steps: int = 3) -> Image.Image:
        W, H   = VIDEO_WIDTH, VIDEO_HEIGHT
        margin = 72
        max_w  = W - 2 * margin
        kind   = section.get("kind", "hook")

        # ── Background ──
        img  = _gradient_bg(self.bg_top, self.bg_bot)
        draw = ImageDraw.Draw(img, "RGBA")

        # Subtle diagonal stripe overlay (decorative)
        stripe_col = (255, 255, 255, 6)
        for sx in range(-H, W, 120):
            draw.polygon(
                [(sx, 0), (sx + 80, 0), (sx + 80 + H, H), (sx + H, H)],
                fill=stripe_col,
            )

        # ── Fonts ──
        f_channel  = _font(FONT_REG,  30)
        f_progress = _font(FONT_BOLD, 28)
        f_label    = _font(FONT_BOLD, 28)
        f_title    = _font(FONT_BOLD, 68)
        f_subtitle = _font(FONT_REG,  42)
        f_body     = _font(FONT_REG,  40)
        f_caption  = _font(FONT_BOLD, 34)
        f_icon     = _font(FONT_BOLD, 30)
        f_cta_bar  = _font(FONT_REG,  32)
        f_step_num = _font(FONT_BOLD, 38)

        white = self.text_color    # "#FFFFFF"
        amber = self.accent        # "#FF8C00"

        # ── Top bar: channel badge + progress ──
        # Channel badge
        badge = CHANNEL_NAME
        bw = _text_w(draw, badge, f_channel)
        bh = _text_h(draw, badge, f_channel)
        _draw_rounded_rect(draw, (margin, 48, margin + bw + 28, 48 + bh + 18),
                           radius=10, fill=(15, 35, 60))
        draw.text((margin + 14, 54), badge, font=f_channel, fill="#94a3b8")

        # Progress badge (e.g. "2/5")
        pb = _text_w(draw, progress, f_progress)
        ph = _text_h(draw, progress, f_progress)
        px = W - margin - pb - 24
        _draw_rounded_rect(draw, (px, 48, px + pb + 24, 48 + ph + 18),
                           radius=10, fill=(15, 35, 60),
                           outline=amber, width=2)
        draw.text((px + 12, 54), progress, font=f_progress, fill=amber)

        # ── Logo (if exists) ──
        if CHANNEL_LOGO_PATH and os.path.exists(CHANNEL_LOGO_PATH):
            try:
                logo = Image.open(CHANNEL_LOGO_PATH).convert("RGBA")
                logo.thumbnail((90, 90))
                img.paste(logo, (W - margin - 90, 120), logo)
            except Exception:
                pass

        # ── KIND-SPECIFIC content ──────────────────────────────────────────

        if kind == "hook":
            self._render_hook_slide(draw, img, section, margin, max_w, W, H,
                                    f_label, f_title, f_subtitle, f_icon,
                                    white, amber)

        elif kind == "step":
            self._render_step_slide(draw, img, section, margin, max_w, W, H,
                                    f_label, f_title, f_body, f_step_num, f_icon,
                                    white, amber, total_steps)

        elif kind == "cta":
            self._render_cta_slide(draw, img, section, margin, max_w, W, H,
                                   f_label, f_title, f_subtitle, f_icon,
                                   white, amber)

        # ── Burned-in caption (bottom, word-for-word with voiceover) ──
        cap = section.get("caption", "")
        if cap:
            self._render_caption_bar(draw, cap, W, H, margin, f_caption, white)

        # ── Bottom CTA bar ──
        bar_y = H - 118
        draw.rectangle([(margin, bar_y), (W - margin, bar_y + 4)], fill=_hex_rgb(amber))
        ctaw = _text_w(draw, CHANNEL_CTA, f_cta_bar)
        draw.text(((W - ctaw) // 2, bar_y + 16), CHANNEL_CTA,
                  font=f_cta_bar, fill=amber)

        return img

    # ── Slide sub-renderers ───────────────────────────────────────────────────

    def _render_hook_slide(self, draw, img, section, margin, max_w, W, H,
                           f_label, f_title, f_subtitle, f_icon, white, amber):
        y = 170

        # Large icon circle at top
        _draw_icon_circle(draw, W // 2, y + 55, 55, "TIP", amber, f_icon)
        y += 140

        # Horizontal rule
        _draw_horizontal_rule(draw, y, margin, amber)
        y += 28

        # Label pill
        label = section.get("label", "TODAY'S TIP")
        lw = _text_w(draw, label, f_label)
        lh = _text_h(draw, label, f_label)
        _draw_rounded_rect(draw, (margin, y, margin + lw + 28, y + lh + 16),
                           radius=8, fill=_hex_rgb(amber))
        draw.text((margin + 14, y + 8), label, font=f_label, fill=white)
        y += lh + 40

        # Title (large, centred, wrapped)
        title_lines = _wrap(draw, section.get("title", ""), f_title, max_w)
        for line in title_lines:
            lw2 = _text_w(draw, line, f_title)
            lh2 = _text_h(draw, line, f_title)
            # Subtle text shadow
            draw.text(((W - lw2) // 2 + 2, y + 2), line, font=f_title, fill=(0, 0, 0))
            draw.text(((W - lw2) // 2, y), line, font=f_title, fill=white)
            y += lh2 + 16

        # Subtitle if present
        sub = section.get("subtitle", "")
        if sub:
            y += 20
            for line in _wrap(draw, sub, f_subtitle, max_w):
                lw3 = _text_w(draw, line, f_subtitle)
                draw.text(((W - lw3) // 2, y), line, font=f_subtitle, fill="#CBD5E1")
                y += _text_h(draw, line, f_subtitle) + 12

        # Three teaser step indicators
        y = max(y + 40, 800)
        self._draw_step_teasers(draw, W, y, margin, amber, white)

    def _draw_step_teasers(self, draw, W, y, margin, amber, white):
        """Three numbered dots hinting at the 3 steps ahead."""
        f_num = _font(FONT_BOLD, 26)
        labels = ["1", "2", "3"]
        dot_r  = 32
        spacing = 160
        cx0 = W // 2 - spacing
        for i, lbl in enumerate(labels):
            cx = cx0 + i * spacing
            # Outline circle (unfilled)
            draw.ellipse([cx - dot_r, y - dot_r, cx + dot_r, y + dot_r],
                         outline=_hex_rgb(amber), width=3)
            tw = _text_w(draw, lbl, f_num)
            th = _text_h(draw, lbl, f_num)
            draw.text((cx - tw // 2, y - th // 2 - 2), lbl, font=f_num, fill=amber)
        # Connecting lines
        for i in range(len(labels) - 1):
            x_start = cx0 + i * spacing + dot_r
            x_end   = cx0 + (i + 1) * spacing - dot_r
            draw.rectangle([(x_start, y - 2), (x_end, y + 2)],
                           fill=_hex_rgb(amber))

    def _render_step_slide(self, draw, img, section, margin, max_w, W, H,
                           f_label, f_title, f_body, f_step_num, f_icon,
                           white, amber, total_steps):
        step_num = section.get("step_num", 1)
        y = 160

        # Large circle icon with step number
        _draw_icon_circle(draw, W // 2, y + 65, 65, str(step_num), amber, f_step_num)
        y += 165

        # Horizontal rule
        _draw_horizontal_rule(draw, y, margin, amber)
        y += 28

        # STEP N label pill
        label = section.get("label", f"STEP {step_num}")
        lw = _text_w(draw, label, f_label)
        lh = _text_h(draw, label, f_label)
        _draw_rounded_rect(draw, (margin, y, margin + lw + 28, y + lh + 16),
                           radius=8, fill=_hex_rgb(amber))
        draw.text((margin + 14, y + 8), label, font=f_label, fill=white)
        y += lh + 44

        # Main title (content of the step)
        title_lines = _wrap(draw, section.get("title", ""), f_title, max_w)
        for line in title_lines:
            lw2 = _text_w(draw, line, f_title)
            # Shadow
            draw.text(((W - lw2) // 2 + 2, y + 2), line, font=f_title, fill=(0, 0, 0))
            draw.text(((W - lw2) // 2, y), line, font=f_title, fill=white)
            y += _text_h(draw, line, f_title) + 16

        # Card background for body detail
        card_top = y + 20
        card_bot = card_top + 300
        draw.rounded_rectangle(
            [margin - 10, card_top, W - margin + 10, card_bot],
            radius=20,
            fill=(10, 40, 80),
            outline=_hex_rgb(amber),
            width=2,
        )

        # Detail text inside card (re-use subtitle if available, else title)
        detail = section.get("subtitle") or section.get("title", "")
        detail_y = card_top + 30
        for line in _wrap(draw, detail, f_body, max_w - 40):
            lw3 = _text_w(draw, line, f_body)
            draw.text(((W - lw3) // 2, detail_y), line, font=f_body, fill="#E2E8F0")
            detail_y += _text_h(draw, line, f_body) + 14

        # Progress dots at bottom of card area
        dot_y = card_bot + 50
        self._draw_progress_dots(draw, W, dot_y, step_num, total_steps, amber)

    def _draw_progress_dots(self, draw, W, y, current, total, amber):
        """Filled/unfilled dots showing which step we're on."""
        r = 14
        spacing = 48
        cx0 = W // 2 - (total - 1) * spacing // 2
        for i in range(total):
            cx = cx0 + i * spacing
            if i + 1 <= current:
                draw.ellipse([cx - r, y - r, cx + r, y + r], fill=_hex_rgb(amber))
            else:
                draw.ellipse([cx - r, y - r, cx + r, y + r],
                             outline=_hex_rgb(amber), width=3)

    def _render_cta_slide(self, draw, img, section, margin, max_w, W, H,
                          f_label, f_title, f_subtitle, f_icon, white, amber):
        y = 160

        # Save icon (bookmark-style drawn shape)
        self._draw_bookmark_icon(draw, W // 2, y + 65, amber)
        y += 165

        # Rule
        _draw_horizontal_rule(draw, y, margin, amber)
        y += 28

        # Label
        label = "SAVE THIS"
        lw = _text_w(draw, label, f_label)
        lh = _text_h(draw, label, f_label)
        _draw_rounded_rect(draw, (margin, y, margin + lw + 28, y + lh + 16),
                           radius=8, fill=_hex_rgb(amber))
        draw.text((margin + 14, y + 8), label, font=f_label, fill=white)
        y += lh + 44

        # Title
        title_lines = _wrap(draw, section.get("title", ""), f_title, max_w)
        for line in title_lines:
            lw2 = _text_w(draw, line, f_title)
            draw.text(((W - lw2) // 2 + 2, y + 2), line, font=f_title, fill=(0, 0, 0))
            draw.text(((W - lw2) // 2, y), line, font=f_title, fill=white)
            y += _text_h(draw, line, f_title) + 16

        # Subtitle
        sub = section.get("subtitle", "")
        if sub:
            y += 24
            for line in _wrap(draw, sub, f_subtitle, max_w):
                lw3 = _text_w(draw, line, f_subtitle)
                draw.text(((W - lw3) // 2, y), line, font=f_subtitle, fill="#CBD5E1")
                y += _text_h(draw, line, f_subtitle) + 12

        # Recap card: 3 steps summary
        y = max(y + 40, 900)
        card_top = y
        card_bot = card_top + 230
        draw.rounded_rectangle(
            [margin - 10, card_top, W - margin + 10, card_bot],
            radius=20,
            fill=(10, 40, 80),
            outline=_hex_rgb(amber),
            width=2,
        )
        f_recap = _font(FONT_BOLD, 30)
        recap_labels = ["Step 1", "Step 2", "Step 3"]
        ry = card_top + 22
        for lbl in recap_labels:
            draw.text((margin + 20, ry), f"✓  {lbl}", font=f_recap, fill=amber)
            ry += _text_h(draw, lbl, f_recap) + 16

    def _draw_bookmark_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, amber: str):
        """Draw a simple bookmark shape (rectangle with V cutout at bottom)."""
        acc = _hex_rgb(amber)
        w, h = 70, 90
        x0, y0 = cx - w // 2, cy - h // 2
        x1, y1 = cx + w // 2, cy + h // 2
        # Body
        draw.rectangle([x0, y0, x1, y1], fill=acc)
        # V notch at bottom
        mid = cx
        draw.polygon([(x0, y1), (mid, y1 - 25), (x1, y1)], fill=_hex_rgb(self.bg_top))

    def _render_caption_bar(self, draw, cap: str, W: int, H: int,
                            margin: int, f_caption, white: str):
        """Semi-transparent bar at bottom with burned-in captions."""
        cap_y = H - 300
        bar_height = 160
        # Dark semi-transparent backing
        overlay = Image.new("RGBA", (W, bar_height), (0, 0, 0, 140))
        # We can't composite RGBA onto the draw directly — handled via img.paste below
        # Instead draw opaque rounded rect
        draw.rounded_rectangle(
            [margin - 20, cap_y - 10, W - margin + 20, cap_y + bar_height],
            radius=16,
            fill=(5, 15, 35),
        )

        cap_lines: List[str] = []
        for part in cap.split("\n"):
            part = part.strip()
            if part:
                cap_lines.extend(_wrap(draw, part, f_caption, W - 2 * margin - 20))

        y = cap_y + 8
        for line in cap_lines:
            lw = _text_w(draw, line, f_caption)
            tx = (W - lw) // 2
            # Shadow
            draw.text((tx + 2, y + 2), line, font=f_caption, fill=(0, 0, 0))
            draw.text((tx, y), line, font=f_caption, fill=white)
            y += _text_h(draw, line, f_caption) + 10

    # ── TTS / audio / video helpers ───────────────────────────────────────────

    async def _tts(self, text: str, path: str) -> bool:
        import edge_tts
        comm = edge_tts.Communicate(text.strip(), self.voice, rate="+5%")
        await comm.save(path)
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

    def _fit_audio_to_duration(self, src: str, dst: str, target: float) -> bool:
        dur = self._probe_duration(src)
        if dur <= 0:
            return False
        if dur > target:
            af = f"atrim=0:{target:.3f}"
        elif dur < target - 0.05:
            speed = min(dur / target, 1.0)
            tempo = min(2.0, max(1.0, 1.0 / speed)) if speed < 0.98 else 1.0
            pad = min(0.5, max(0, target - dur / tempo))
            af = f"atempo={tempo:.4f},apad=pad_dur={pad:.3f}"
        else:
            pad = min(0.5, max(0, target - dur))
            af = f"apad=pad_dur={pad:.3f}"
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-af", af, "-t", f"{target:.3f}",
            "-c:a", "libmp3lame", "-q:a", "4", dst,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0 and os.path.exists(dst)

    def _image_to_segment(self, png: str, duration: float, seg_path: str) -> bool:
        fps    = TIP_FPS
        frames = max(int(duration * fps), 2)
        z_expr = "1.05-0.05*on/(max(on-1\\,1))"
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
            print(f"[TipVideoBuilder] Segment error: {result.stderr[-300:]}")
        return result.returncode == 0

    def _concat_video_xfade(self, segments: List[str], durations: List[float], out: str) -> bool:
        if len(segments) == 1:
            shutil.copy(segments[0], out)
            return True

        xfade  = self.xfade
        inputs = []
        for seg in segments:
            inputs.extend(["-i", seg])

        if len(segments) == 2:
            offset = max(durations[0] - xfade, 0.1)
            fc = f"[0:v][1:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[vout]"
        else:
            parts       = []
            offset      = max(durations[0] - xfade, 0.1)
            parts.append(
                f"[0:v][1:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[v01]"
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
            # Fallback: simple concat
            print("[TipVideoBuilder] xfade failed — using concat fallback")
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

    def _final_mux(self, video: str, voice: str, output: str) -> bool:
        bgm = BACKGROUND_MUSIC_PATH
        t   = TIP_TOTAL_DURATION
        if bgm and os.path.exists(bgm):
            fc = (
                "[1:a]volume=1.0[v];[2:a]volume=0.1,aloop=loop=-1:size=2e+09[m];"
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

    # ── Public build entry-point ──────────────────────────────────────────────

    def build(self, tip: Dict, output_path: Optional[str] = None) -> Optional[str]:
        sections    = self._sections_from_tip(tip)
        total_steps = sum(1 for s in sections if s["kind"] == "step")
        total_slides = len(sections)

        if output_path is None:
            from datetime import date
            output_path = os.path.join(
                QUEUE_OUTPUT_FOLDER,
                f"tip_{tip.get('generated_on', date.today().isoformat())}.mp4",
            )

        work = tempfile.mkdtemp(prefix="tip_build_")
        try:
            # ── TTS per slide ──
            fitted_audio = []
            for i, sec in enumerate(sections):
                raw    = os.path.join(work, f"voice_raw_{i}.mp3")
                fitted = os.path.join(work, f"voice_fit_{i}.mp3")
                voice_text = (sec.get("voice") or sec.get("caption") or "").strip()
                if not voice_text:
                    voice_text = sec.get("title", "Tip")
                try:
                    ok = asyncio.run(self._tts(voice_text, raw))
                except Exception as e:
                    print(f"[TipVideoBuilder] TTS error slide {i}: {e}")
                    return None
                if not ok or not self._fit_audio_to_duration(raw, fitted, sec["duration"]):
                    print(f"[TipVideoBuilder] Audio fit failed for slide {i}")
                    return None
                fitted_audio.append(fitted)

            # ── Render slides → video segments ──
            seg_paths, durations = [], []
            for i, sec in enumerate(sections):
                progress = f"{i + 1}/{total_slides}"
                slide    = self._render_slide(sec, progress, total_steps=total_steps)
                png      = os.path.join(work, f"slide_{i}.png")
                slide.save(png, quality=95)
                dur = sec["duration"]
                seg = os.path.join(work, f"seg_{i}.mp4")
                if not self._image_to_segment(png, dur, seg):
                    print(f"[TipVideoBuilder] Segment failed for slide {i}")
                    return None
                seg_paths.append(seg)
                durations.append(dur)

            # ── Assemble ──
            video_only = os.path.join(work, "video_xfade.mp4")
            if not self._concat_video_xfade(seg_paths, durations, video_only):
                return None

            voice_full = self._merge_audio(fitted_audio, work)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            if not self._final_mux(video_only, voice_full, output_path):
                return None

            # Force exact target duration
            exact = os.path.join(work, "exact.mp4")
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", output_path,
                    "-vf", f"tpad=stop_mode=clone:stop_duration={max(0, TIP_TOTAL_DURATION)}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TIP_FPS),
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{TIP_TOTAL_DURATION:.3f}",
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
                f"({mb:.1f} MB, {actual:.2f}s / target {TIP_TOTAL_DURATION}s)"
            )
            return output_path

        finally:
            shutil.rmtree(work, ignore_errors=True)