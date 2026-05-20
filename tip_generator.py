"""
Generate daily English tip scripts for faceless Shorts (Idea 2).
"""
import json
import hashlib
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL, TIP_NICHE, QUEUE_OUTPUT_FOLDER, CHANNEL_NAME

client = genai.Client(api_key=GEMINI_API_KEY)

TIP_HISTORY_FILE = Path(QUEUE_OUTPUT_FOLDER) / ".tip_history.json"

# Emojis: Hook 📧 | Step1 📤 | Step2 📂 | Step3 ⏱️ | CTA 💾
SLIDE_EMOJIS = ["📧", "📤", "📂", "⏱️", "💾"]

FALLBACK_TIPS: List[Dict] = [
    {
        "slide_emojis": SLIDE_EMOJIS,
        "hook": "You're wasting 2 hours daily on email",
        "hook_voice": "You're wasting 2 hours daily on email",
        "tip_title": "3-step inbox system",
        "steps": [
            {
                "emoji": "📤",
                "caption": "Unsubscribe from 3 lists you never read",
                "line": "Unsubscribe from 3 lists you never read",
                "voice": "Unsubscribe from 3 lists you never read",
            },
            {
                "emoji": "📂",
                "caption": "Sort into Action and Archive folders",
                "line": "Sort into Action and Archive folders",
                "voice": "Sort into Action and Archive folders",
            },
            {
                "emoji": "⏱️",
                "caption": "Under 2 minutes? Reply immediately",
                "line": "Under 2 minutes? Reply immediately",
                "voice": "Under 2 minutes? Reply immediately",
            },
        ],
        "cta_line1": "Save this to clean your inbox tomorrow 📩",
        "cta_line2": "Comment 'DONE' when you try it!",
        "cta_voice": "Save this to clean your inbox tomorrow. Comment 'DONE' when you try it!",
        "script": (
            "You're wasting 2 hours daily on email. "
            "Unsubscribe from 3 lists you never read. "
            "Sort into Action and Archive folders. "
            "Under 2 minutes? Reply immediately. "
            "Save this to clean your inbox tomorrow. Comment DONE when you try it!"
        ),
        "suggested_titles": [
            "Stop Wasting 2 Hours on Email — 3-Step Fix #Shorts",
            "Inbox Hack That Actually Works #Shorts",
        ],
        "suggested_description": (
            "3 connected email productivity steps you can use today. "
            f"Follow {CHANNEL_NAME} for daily English tips."
        ),
        "tags": ["#email", "#productivity", "#inbox", "#shorts"],
        "hot_words": ["email", "productivity", "inbox", "tips"],
        "main_topic": "Education",
    },
    {
        "hook": "Still can't focus for more than 10 minutes?",
        "hook_subtitle": "Try this 3-step phone hack",
        "hook_emoji": "🎯",
        "hook_voice": "Still can't focus for more than ten minutes? Try this three step phone hack.",
        "tip_title": "Deep focus in 3 steps",
        "steps": [
            {
                "emoji": "📱",
                "title": "Hide distractions",
                "line": "Move social apps off home screen",
                "voice": "Step one: move social apps off your home screen.",
            },
            {
                "emoji": "🔕",
                "title": "Block notifications",
                "line": "Do Not Disturb for 1 hour",
                "voice": "Step two: turn on Do Not Disturb for one focused hour.",
            },
            {
                "emoji": "🚪",
                "title": "Physical distance",
                "line": "Phone in another room",
                "voice": "Step three: put your phone in another room while you work.",
            },
        ],
        "cta_voice": "Follow for daily focus and productivity tips.",
        "script": "Still can't focus? Hide social apps, use Do Not Disturb for one hour, and put your phone in another room.",
        "suggested_titles": ["3-Step Focus Hack #Shorts", "How to Focus Without Willpower #Shorts"],
        "suggested_description": "Daily focus tips in English.",
        "tags": ["#focus", "#productivity", "#shorts"],
        "hot_words": ["focus", "productivity", "deep work"],
        "main_topic": "Education",
    },
    {
        "hook": "ChatGPT giving you weak answers?",
        "hook_subtitle": "Use this 3-part prompt",
        "hook_emoji": "🤖",
        "hook_voice": "ChatGPT giving you weak answers? Use this three part prompt formula.",
        "tip_title": "Better AI prompts",
        "steps": [
            {
                "emoji": "🎭",
                "title": "Set the role",
                "line": "Act as an expert in your field",
                "voice": "Step one: tell the AI what role to play, like act as a career coach.",
            },
            {
                "emoji": "📋",
                "title": "Define the task",
                "line": "One clear sentence + format",
                "voice": "Step two: give one clear task and the format you want, like three bullet points.",
            },
            {
                "emoji": "📏",
                "title": "Add constraints",
                "line": "Word limit + audience",
                "voice": "Step three: add constraints like word limit and who it is for.",
            },
        ],
        "cta_voice": "Follow for daily AI tips in English.",
        "script": "Use role, task, and constraints for better ChatGPT answers every time.",
        "suggested_titles": ["ChatGPT Prompt Formula #Shorts", "Better AI Prompts in 30 Seconds #Shorts"],
        "suggested_description": "Daily AI and productivity tips.",
        "tags": ["#chatgpt", "#ai", "#prompts", "#shorts"],
        "hot_words": ["chatgpt", "ai", "prompts"],
        "main_topic": "Science & Technology",
    },
]


class TipGenerator:
    def __init__(self, niche: Optional[str] = None):
        self.niche = niche or TIP_NICHE
        self.client = client
        Path(QUEUE_OUTPUT_FOLDER).mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> List[str]:
        if not TIP_HISTORY_FILE.exists():
            return []
        try:
            with open(TIP_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("titles", [])
        except Exception:
            return []

    def _save_history(self, tip: Dict) -> None:
        titles = self._load_history()
        title = tip.get("tip_title", "")
        if title and title not in titles:
            titles.append(title)
        with open(TIP_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"titles": titles[-60:]}, f, indent=2)

    def _tip_hash(self, tip: Dict) -> str:
        key = f"{tip.get('tip_title', '')}:{tip.get('hook', '')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def _parse_response(self, text: str) -> Dict:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
        return json.loads(text.strip())

    def _fallback_tip(self, topic: Optional[str] = None) -> Dict:
        """
        Fallback that always produces a coherent Short.

        If a topic is provided (content-queue mode), we generate a topic-aligned 3-step
        script instead of reusing a static inbox tip (so every video isn't identical).
        """
        if topic:
            title = topic.strip().rstrip("?")[:60]
            hook = topic.strip()[:80]
            # Generic 3-step framework that fits most topics
            steps = [
                "Pick one goal for today",
                "Practice 20 minutes daily",
                "Prove it with one project",
            ]
            tip = {
                "slide_emojis": SLIDE_EMOJIS,
                "hook": hook[:80],
                "hook_voice": hook[:80],
                "tip_title": title[:60],
                "steps": [
                    {"emoji": "📤", "caption": steps[0], "line": steps[0], "voice": steps[0]},
                    {"emoji": "📂", "caption": steps[1], "line": steps[1], "voice": steps[1]},
                    {"emoji": "⏱️", "caption": steps[2], "line": steps[2], "voice": steps[2]},
                ],
                "cta_line1": "Save this and try it today",
                "cta_line2": "Comment 'DONE' when you try it!",
                "cta_voice": "Save this and try it today. Comment DONE when you try it!",
                "script": (
                    f"{hook}. {steps[0]}. {steps[1]}. {steps[2]}. "
                    "Save this and try it today. Comment DONE when you try it!"
                ),
                "suggested_titles": [f"{title[:55]} #Shorts"],
                "suggested_description": (
                    f"{topic}\n\n"
                    f"Daily {self.niche} tips in English. Follow {CHANNEL_NAME} for more."
                ),
                "tags": ["#shorts", "#tips", "#productivity"],
                "hot_words": [w for w in title.lower().split()[:6]],
                "main_topic": "Education",
                "source": "fallback",
                "niche": self.niche,
                "queue_topic": topic,
            }
            return tip

        # Non-topic fallback (kept for compatibility)
        day_index = date.today().toordinal() % len(FALLBACK_TIPS)
        tip = dict(FALLBACK_TIPS[day_index])
        tip["source"] = "fallback"
        tip["niche"] = self.niche
        return tip

    def generate(
        self,
        avoid_titles: Optional[List[str]] = None,
        topic: Optional[str] = None,
    ) -> Dict:
        avoid = avoid_titles if avoid_titles is not None else self._load_history()
        avoid_str = ", ".join(avoid[-15:]) if avoid else "none"

        if topic:
            focus = f"""TOPIC (center the entire Short on this — hook must mention it):
"{topic}"
Niche context: {self.niche}
The 3 steps should directly answer or break down this topic (lists, tips, or steps as appropriate)."""
        else:
            focus = f"Niche: {self.niche}"

        prompt = f"""Create ONE English YouTube Short.
{focus}

Return ONLY valid JSON (no markdown).

RULES:
- slide_emojis: ["📧","📤","📂","⏱️","💾"]
- hook and hook_voice MUST be identical words (max 12 words)
- Each step: caption, line, and voice MUST be the exact same string (max 10 words)
- cta_line1: short, generic, topic-relevant (max 10 words). Examples:
  - "Save this and try it today"
  - "Save this for your next interview"
- cta_line2: "Comment 'DONE' when you try it!"
- cta_voice: speak cta_line1 then cta_line2 word-for-word (no extra words)
- 3 logical connected steps. Avoid: {avoid_str}

{{
  "slide_emojis": ["📧","📤","📂","⏱️","💾"],
  "hook": "Same text as hook_voice",
  "hook_voice": "Same text as hook",
  "tip_title": "Internal title",
  "steps": [
    {{"emoji":"📤","caption":"short line","line":"same as caption","voice":"same as caption"}},
    {{"emoji":"📂","caption":"...","line":"...","voice":"..."}},
    {{"emoji":"⏱️","caption":"...","line":"...","voice":"..."}}
  ],
  "cta_line1": "Save this and try it today",
  "cta_line2": "Comment 'DONE' when you try it!",
  "cta_voice": "Save this and try it today. Comment DONE when you try it!",
  "on_screen_lines": ["step1 caption","step2","step3"],
  "suggested_titles": ["Title #Shorts"],
  "suggested_description": "Description",
  "tags": ["#shorts"],
  "hot_words": ["kw1"],
  "main_topic": "Education"
}}"""

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt,
            )
            tip = self._parse_response(response.text or "")
            tip["source"] = "gemini"
            tip["niche"] = self.niche
            if topic:
                tip["queue_topic"] = topic
            tip["generated_on"] = date.today().isoformat()
            if not tip.get("on_screen_lines") and tip.get("steps"):
                tip["on_screen_lines"] = [s.get("line", "") for s in tip["steps"][:3]]
            self._save_history(tip)
            return tip
        except Exception as e:
            print(f"[TipGenerator] Gemini failed ({e}), using fallback tip")
            tip = self._fallback_tip(topic=topic)
            tip["generated_on"] = date.today().isoformat()
            self._save_history(tip)
            return tip

    def save_tip_json(self, tip: Dict, output_dir: Optional[str] = None) -> str:
        folder = Path(output_dir or QUEUE_OUTPUT_FOLDER)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"tip_{date.today().isoformat()}_{self._tip_hash(tip)}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tip, f, indent=2)
        return str(path)
