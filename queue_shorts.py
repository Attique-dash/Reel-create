"""
Queue pipeline: random line from content file → Gemini script → TTS video → save → upload.
"""
import hashlib
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

from config import CONTENT_QUEUE_FILE, QUEUE_OUTPUT_FOLDER, TIP_NICHE
from content_queue import ContentQueue
from tip_generator import TipGenerator, apply_priority_fixes, parse_step_count
from tip_video_builder import TipVideoBuilder


class QueueVideoPipeline:
    """Create one original Short from a topic line (random or fixed)."""

    def __init__(
        self,
        content_file: Optional[str] = None,
        voice: Optional[str] = None,
    ):
        self.queue = ContentQueue(file_path=content_file)
        self.generator = TipGenerator(niche=TIP_NICHE)
        self.builder = TipVideoBuilder(voice=voice)
        Path(QUEUE_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    def _output_path(self, topic: str, slot: Optional[str] = None) -> str:
        slug = hashlib.md5(topic.encode()).hexdigest()[:8]
        day = date.today().isoformat()
        time_part = datetime.now().strftime("%H%M")
        slot_part = f"_{slot}" if slot else f"_{time_part}"
        name = f"video_{day}{slot_part}_{slug}.mp4"
        return os.path.join(QUEUE_OUTPUT_FOLDER, name)

    def tip_to_analysis(self, tip: Dict, topic: str) -> Dict:
        titles = tip.get("suggested_titles") or [topic[:60]]
        return {
            "suggested_titles": titles,
            "suggested_description": tip.get(
                "suggested_description",
                f"{topic}\n\nFollow for more Shorts.",
            ),
            "tags": tip.get("tags", ["#shorts", "#tips"]),
            "hot_words": tip.get("hot_words", []),
            "main_topic": tip.get("main_topic", "Education"),
            "hook": tip.get("hook", topic[:80]),
            "tip_title": tip.get("tip_title", topic[:40]),
        }

    def run(
        self,
        topic: Optional[str] = None,
        line_index: Optional[int] = None,
        upload: bool = False,
        privacy: str = "private",
        uploader=None,
        slot: Optional[str] = None,
        mark_line_used: bool = True,
    ) -> Dict:
        """
        Full run: pick or use topic → generate → build MP4 → optional YouTube upload.
        """
        picked_index: Optional[int] = line_index

        if topic is None:
            picked_index, topic = self.queue.pick_random_line()
            print(f"\n🎲 Random topic (line {picked_index + 1}): {topic}")
        else:
            print(f"\n📝 Topic: {topic}")

        print("   Step 1/3: Generating script with AI...")
        tip = self.generator.generate(topic=topic)
        tip["queue_topic"] = topic
        tip = apply_priority_fixes(tip, topic)
        n = parse_step_count(topic, tip)
        print(f"   Tips in video: {n} (+ 1 topic slide + 1 save slide = {n + 2} slides)")
        tip["queue_line_index"] = picked_index
        tip["generated_on"] = date.today().isoformat()

        json_path = self._save_json(tip, topic)
        print(f"   💾 Script JSON → {json_path}")
        print(f"   Hook : {tip.get('hook', '')}")

        print("   Step 2/3: Building faceless Short (TTS + slides)...")
        video_path = self._output_path(topic, slot=slot)
        video_path = self.builder.build(tip, output_path=video_path)
        if not video_path:
            raise RuntimeError("Failed to create queue Short video")

        if mark_line_used and picked_index is not None:
            self.queue.mark_used(picked_index, topic, video_path)

        result: Dict = {
            "topic": topic,
            "line_index": picked_index,
            "tip": tip,
            "json_path": json_path,
            "video_path": video_path,
            "uploaded": False,
            "youtube_id": None,
        }

        if upload:
            print("   Step 3/3: Uploading to YouTube...")
            if uploader is None:
                from youtube_uploader import YouTubeUploader
                uploader = YouTubeUploader()
            analysis = self.tip_to_analysis(tip, topic)
            resp = uploader.upload_short(video_path, analysis, privacy_status=privacy)
            if resp:
                result["uploaded"] = True
                result["youtube_id"] = resp.get("id")
                print(f"   ✅ https://youtube.com/shorts/{resp['id']}")
            else:
                print("   ❌ Upload failed")
        else:
            print("   Step 3/3: Upload skipped (use --upload)")

        return result

    def _save_json(self, tip: Dict, topic: str) -> str:
        folder = Path(QUEUE_OUTPUT_FOLDER)
        slug = hashlib.md5(topic.encode()).hexdigest()[:8]
        path = folder / f"video_{date.today().isoformat()}_{slug}.json"
        with open(path, "w", encoding="utf-8") as f:
            import json
            json.dump(tip, f, indent=2)
        return str(path)
