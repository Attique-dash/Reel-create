"""
Build 9:16 tip Shorts — fixed 28s timing, branded slides, burned-in captions, TTS.
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

# Slide emojis: Hook | Step1 | Step2 | Step3 | CTA
SLIDE_EMOJIS = ["📧", "📤", "📂", "⏱️", "💾"]

FONT_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_REG = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _font(paths: List[str], size: int):
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> List[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def _solid_bg(color: str) -> Image.Image:
    return Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), _hex_rgb(color))


class TipVideoBuilder:
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or TTS_VOICE
        self.bg = TIP_BG_COLOR
        self.accent = TIP_BRAND_COLOR
        self.text_color = TIP_TEXT_COLOR
        self.slide_durations = list(TIP_SLIDE_DURATIONS)
        self.xfade = TIP_XFADE_DURATION
        Path(QUEUE_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    def _sections_from_tip(self, tip: Dict) -> List[Dict]:
        """Five slides: hook + 3 steps + CTA. Voice/caption word-for-word."""
        emojis = tip.get("slide_emojis") or SLIDE_EMOJIS

        hook_caption = tip.get("hook", "")
        hook_voice = tip.get("hook_voice") or hook_caption

        sections = [{
            "kind": "hook",
            "emoji": emojis[0],
            "title": hook_caption,
            "caption": hook_caption,
            "voice": hook_voice,
            "duration": self.slide_durations[0],
        }]

        steps = tip.get("steps") or []
        for i in range(3):
            if i < len(steps):
                step = steps[i]
                cap = step.get("caption") or step.get("line") or step.get("title", "")
                voice = step.get("voice") or cap
            else:
                lines = tip.get("on_screen_lines") or []
                cap = lines[i] if i < len(lines) else f"Step {i + 1}"
                voice = cap
            sections.append({
                "kind": "step",
                "step_num": i + 1,
                "emoji": emojis[i + 1] if i + 1 < len(emojis) else "✅",
                "title": cap,
                "caption": cap,
                "voice": voice,
                "duration": self.slide_durations[i + 1],
            })

        cta_line1 = tip.get("cta_line1", "Save this to clean your inbox tomorrow 📩")
        cta_line2 = tip.get("cta_line2", "Comment 'DONE' when you try it!")
        cta_caption = f"{cta_line1}\n{cta_line2}"
        cta_voice = tip.get("cta_voice") or f"{cta_line1} {cta_line2}"

        sections.append({
            "kind": "cta",
            "emoji": emojis[4] if len(emojis) > 4 else "💾",
            "title": cta_line1,
            "subtitle": cta_line2,
            "caption": cta_caption,
            "voice": cta_voice,
            "duration": self.slide_durations[4],
        })
        return sections

    def _render_slide(self, section: Dict, progress: str) -> Image.Image:
        img = _solid_bg(self.bg)
        draw = ImageDraw.Draw(img)
        margin = 72
        max_w = VIDEO_WIDTH - 2 * margin
        white = self.text_color

        # Top-left: channel name (no emoji prefix — clean brand)
        badge_font = _font(FONT_REG, 30)
        badge = CHANNEL_NAME
        bb = draw.textbbox((0, 0), badge, font=badge_font)
        draw.rounded_rectangle(
            [margin, 48, margin + (bb[2] - bb[0]) + 28, 48 + (bb[3] - bb[1]) + 18],
            radius=10,
            fill=(15, 35, 60),
        )
        draw.text((margin + 14, 54), badge, font=badge_font, fill="#94a3b8")

        # Top-right: progress
        prog_font = _font(FONT_BOLD, 28)
        pb = draw.textbbox((0, 0), progress, font=prog_font)
        px = VIDEO_WIDTH - margin - (pb[2] - pb[0]) - 24
        draw.rounded_rectangle(
            [px, 48, VIDEO_WIDTH - margin, 48 + (pb[3] - pb[1]) + 18],
            radius=10,
            fill=(15, 35, 60),
            outline=self.accent,
            width=2,
        )
        draw.text((px + 12, 54), progress, font=prog_font, fill=self.accent)

        if CHANNEL_LOGO_PATH and os.path.exists(CHANNEL_LOGO_PATH):
            try:
                logo = Image.open(CHANNEL_LOGO_PATH).convert("RGBA")
                logo.thumbnail((100, 100))
                img.paste(logo, (VIDEO_WIDTH - margin - 100, 120), logo)
            except Exception:
                pass

        # Large emoji (native — not empty squares)
        emoji = section.get("emoji", "")
        y = 175
        if emoji:
            ef = _font(FONT_BOLD, 110)
            eb = draw.textbbox((0, 0), emoji, font=ef)
            draw.text(((VIDEO_WIDTH - eb[2] + eb[0]) // 2, y), emoji, font=ef, fill=white)
            y += 130

        title_font = _font(FONT_BOLD, 64)
        body_font = _font(FONT_REG, 44)

        for line in _wrap(draw, section.get("title", ""), title_font, max_w):
            tb = draw.textbbox((0, 0), line, font=title_font)
            draw.text(
                ((VIDEO_WIDTH - tb[2] + tb[0]) // 2, y), line,
                font=title_font, fill=white,
            )
            y += tb[3] - tb[1] + 14

        sub = section.get("subtitle") or ""
        if sub:
            y += 20
            for line in _wrap(draw, sub, body_font, max_w):
                tb = draw.textbbox((0, 0), line, font=body_font)
                draw.text(
                    ((VIDEO_WIDTH - tb[2] + tb[0]) // 2, y), line,
                    font=body_font, fill="#E2E8F0",
                )
                y += tb[3] - tb[1] + 10

        if section.get("kind") == "step":
            sn = section.get("step_num", 1)
            lf = _font(FONT_BOLD, 30)
            label = f"STEP {sn}"
            lb = draw.textbbox((0, 0), label, font=lf)
            draw.rounded_rectangle(
                [margin, y + 16, margin + lb[2] - lb[0] + 24, y + 16 + lb[3] - lb[1] + 12],
                radius=8,
                fill=self.accent,
            )
            draw.text((margin + 12, y + 22), label, font=lf, fill=white)

        # Burned-in captions (word-for-word with voiceover)
        cap = section.get("caption", "")
        if cap:
            cap_font = _font(FONT_BOLD, 36)
            cap_y = VIDEO_HEIGHT - 300
            cap_lines = []
            if "\n" in cap:
                for part in cap.split("\n"):
                    cap_lines.extend(_wrap(draw, part.strip(), cap_font, max_w - 40))
            else:
                cap_lines = _wrap(draw, cap, cap_font, max_w - 40)
            for line in cap_lines:
                tb = draw.textbbox((0, 0), line, font=cap_font)
                tx = (VIDEO_WIDTH - tb[2] + tb[0]) // 2
                draw.text((tx + 2, cap_y + 2), line, font=cap_font, fill="#000000")
                draw.text((tx, cap_y), line, font=cap_font, fill=white)
                cap_y += tb[3] - tb[1] + 10

        # Bottom orange CTA bar
        bar_y = VIDEO_HEIGHT - 118
        draw.rectangle([(margin, bar_y), (VIDEO_WIDTH - margin, bar_y + 6)], fill=self.accent)
        cta_f = _font(FONT_REG, 32)
        cb = draw.textbbox((0, 0), CHANNEL_CTA, font=cta_f)
        draw.text(
            ((VIDEO_WIDTH - cb[2] + cb[0]) // 2, bar_y + 18),
            CHANNEL_CTA, font=cta_f, fill=self.accent,
        )
        return img

    async def _tts(self, text: str, path: str) -> bool:
        import edge_tts
        # Slightly faster rate to reduce long pauses; still clear
        comm = edge_tts.Communicate(text.strip(), self.voice, rate="+5%")
        await comm.save(path)
        return os.path.exists(path) and os.path.getsize(path) > 100

    def _fit_audio_to_duration(self, src: str, dst: str, target: float) -> bool:
        """Trim or time-stretch voice to exact slide duration (pad max 0.5s)."""
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
            "-af", af,
            "-t", f"{target:.3f}",
            "-c:a", "libmp3lame", "-q:a", "4", dst,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0 and os.path.exists(dst)

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

    def _image_to_segment(self, png: str, duration: float, seg_path: str) -> bool:
        """Zoom 105% → 100% over slide; 30fps; 1080x1920."""
        fps = TIP_FPS
        frames = max(int(duration * fps), 2)
        # z: 1.05 at frame 0 → 1.0 at last frame
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
            print(f"[TipVideoBuilder] Segment: {result.stderr[-280:]}")
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
            fc = f"[0:v][1:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[vout]"
        else:
            parts = []
            offset = max(durations[0] - xfade, 0.1)
            parts.append(f"[0:v][1:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[v01]")
            prev, accumulated = "v01", durations[0] + durations[1] - xfade
            for i in range(2, len(segments)):
                offset = max(accumulated - xfade, 0.1)
                label = "vout" if i == len(segments) - 1 else f"v{i:02d}"
                parts.append(
                    f"[{prev}][{i}:v]xfade=transition=fade:duration={xfade}:offset={offset:.3f}[{label}]"
                )
                prev = label
                accumulated += durations[i] - xfade
            fc = ";".join(parts)

        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[vout]",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TIP_FPS), out]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("[TipVideoBuilder] xfade failed, concat fallback")
            lst = os.path.join(os.path.dirname(out), "vconcat.txt")
            with open(lst, "w") as f:
                for s in segments:
                    f.write(f"file '{s}'\n")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
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
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
            capture_output=True,
        )
        return out if os.path.exists(out) else paths[0]

    def _final_mux(self, video: str, voice: str, output: str) -> bool:
        """Mux and force exactly TIP_TOTAL_DURATION seconds."""
        bgm = BACKGROUND_MUSIC_PATH
        t = TIP_TOTAL_DURATION
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
            print(f"[TipVideoBuilder] Mux: {r.stderr[-300:]}")
        return r.returncode == 0 and os.path.exists(output)

    def build(self, tip: Dict, output_path: Optional[str] = None) -> Optional[str]:
        sections = self._sections_from_tip(tip)
        total_slides = len(sections)

        if output_path is None:
            output_path = os.path.join(QUEUE_OUTPUT_FOLDER, f"tip_{tip.get('generated_on', 'out')}.mp4".replace(":", ""))

        work = tempfile.mkdtemp(prefix="tip_28_")
        try:
            fitted_audio = []
            for i, sec in enumerate(sections):
                raw = os.path.join(work, f"voice_raw_{i}.mp3")
                fitted = os.path.join(work, f"voice_fit_{i}.mp3")
                voice_text = (sec.get("voice") or sec.get("caption") or "").strip()
                if not voice_text:
                    voice_text = sec.get("title", "Tip")
                try:
                    ok = asyncio.run(self._tts(voice_text, raw))
                except Exception as e:
                    print(f"[TipVideoBuilder] TTS error: {e}")
                    return None
                if not ok or not self._fit_audio_to_duration(raw, fitted, sec["duration"]):
                    return None
                fitted_audio.append(fitted)

            seg_paths, durations = [], []
            for i, sec in enumerate(sections):
                progress = f"{i + 1}/{total_slides}"
                slide = self._render_slide(sec, progress)
                png = os.path.join(work, f"slide_{i}.png")
                slide.save(png, quality=95)
                dur = sec["duration"]
                seg = os.path.join(work, f"seg_{i}.mp4")
                if not self._image_to_segment(png, dur, seg):
                    return None
                seg_paths.append(seg)
                durations.append(dur)

            video_only = os.path.join(work, "video_xfade.mp4")
            if not self._concat_video_xfade(seg_paths, durations, video_only):
                return None

            voice_full = self._merge_audio(fitted_audio, work)
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            if not self._final_mux(video_only, voice_full, output_path):
                return None

            # Force exact 28.0s (pad video/audio if xfade made it short)
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
            mb = os.path.getsize(output_path) / (1024 * 1024)
            print(
                f"[TipVideoBuilder] Created: {output_path} "
                f"({mb:.1f} MB, {actual:.2f}s target {TIP_TOTAL_DURATION}s)"
            )
            return output_path
        finally:
            shutil.rmtree(work, ignore_errors=True)
