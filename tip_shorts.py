"""
Idea 2 pipeline: daily English tip → TTS → faceless Short → optional YouTube upload.
"""
import os
from datetime import date
from pathlib import Path
from typing import Dict, Optional

from config import TIPS_OUTPUT_FOLDER, TIP_NICHE
from tip_generator import TipGenerator
from tip_video_builder import TipVideoBuilder


class DailyTipPipeline:
    def __init__(self, niche: Optional[str] = None, voice: Optional[str] = None):
        self.niche = niche or TIP_NICHE
        self.generator = TipGenerator(niche=self.niche)
        self.builder = TipVideoBuilder(voice=voice)
        Path(TIPS_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    def tip_to_analysis(self, tip: Dict) -> Dict:
        """Shape tip metadata for YouTubeUploader.upload_short()."""
        return {
            "suggested_titles": tip.get("suggested_titles", [tip.get("tip_title", "Daily Tip")]),
            "suggested_description": tip.get(
                "suggested_description",
                f"Daily {self.niche} tip. Follow for more Shorts in English.",
            ),
            "tags": tip.get("tags", ["#shorts", "#tips"]),
            "hot_words": tip.get("hot_words", ["tips", "daily", "english"]),
            "main_topic": tip.get("main_topic", "Education"),
            "hook": tip.get("hook", ""),
            "tip_title": tip.get("tip_title", ""),
        }

    def run(
        self,
        upload: bool = False,
        privacy: str = "private",
        uploader=None,
    ) -> Dict:
        """
        Full Idea 2 run: generate tip → build video → optional upload.
        Returns dict with paths and metadata.
        """
        print(f"\n💡 Idea 2 — Daily tip ({self.niche})")
        print("   Step 1/3: Generating script...")
        tip = self.generator.generate()
        json_path = self.generator.save_tip_json(tip)
        print(f"   💾 Tip JSON → {json_path}")
        print(f"   Hook : {tip.get('hook', '')}")
        print(f"   Title: {tip.get('tip_title', '')}")

        print("   Step 2/3: Building faceless Short (TTS + slides)...")
        tip["generated_on"] = date.today().isoformat()
        out_name = f"tip_{date.today().isoformat()}.mp4"
        video_path = os.path.join(TIPS_OUTPUT_FOLDER, out_name)
        video_path = self.builder.build(tip, output_path=video_path)
        if not video_path:
            raise RuntimeError("Failed to create tip Short video")

        result = {
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
            analysis = self.tip_to_analysis(tip)
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
