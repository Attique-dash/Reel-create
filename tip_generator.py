"""
Generate daily English tip scripts for faceless Shorts (Idea 2).
"""
import json
import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


def parse_step_count(topic: Optional[str] = None, tip: Optional[Dict] = None) -> int:
    """
    How many TIP slides (not counting hook or save/CTA).
    Topic title wins: "5 apps" → 5 tips → 7 slides total (hook + 5 + save).
    """
    from_topic: Optional[int] = None
    if topic:
        m = re.search(r"\b(?:top\s+)?(\d+)\b", topic.lower())
        if m:
            from_topic = min(max(int(m.group(1)), 2), 5)

    if from_topic is not None:
        return from_topic

    if tip:
        if tip.get("step_count"):
            return min(max(int(tip["step_count"]), 2), 5)
        steps = tip.get("steps") or []
        if len(steps) >= 2:
            return min(len(steps), 5)
    return 3


# At least 5 unique lines per category so padding never clones the last step.
FALLBACK_STRING_POOLS: Dict[str, List[str]] = {
    "coding": [
        "Solve one easy problem daily",
        "Time yourself under 20 minutes",
        "Review the optimal solution after",
        "Redo missed problems without hints",
        "Explain your approach out loud once",
    ],
    "network": [
        "Message 3 people you admire",
        "Comment value on their posts first",
        "Ask one specific question each time",
        "Follow up within 48 hours",
        "Offer help before you ask for favors",
    ],
    "career": [
        "Document wins weekly in writing",
        "Ask your manager for clear targets",
        "Request a review date in advance",
        "Quantify impact with numbers or quotes",
        "Practice your pitch before the meeting",
    ],
    "learning": [
        "Block 20 minutes daily to study",
        "Build one small project per week",
        "Teach what you learn out loud",
        "Quiz yourself without looking at notes",
        "Ship something tiny every Friday",
    ],
    "productivity": [
        "Pick your top task the night before",
        "Work in 25-minute focused blocks",
        "Review what you finished each day",
        "Batch similar tasks into one block",
        "Say no to one low-value request daily",
    ],
    "ai": [
        "Use role + task + format in prompts",
        "Test two prompts, keep the best",
        "Save your best prompts in a doc",
        "Chain prompts: feed one output into the next",
        "Set a weekly review to refine what works",
    ],
    "freelance": [
        "Pick one skill you already have",
        "Post one offer on a free platform",
        "Deliver fast and ask for a review",
        "Raise price after three happy clients",
        "Reuse one template for every delivery",
    ],
}

GENERIC_FALLBACK_STRINGS = [
    "Apply the smallest version today",
    "Track one result before tomorrow",
    "Adjust based on what actually worked",
    "Remove one blocker that slows you down",
    "Share one lesson so it sticks",
]


def _step_title_key(step) -> str:
    if isinstance(step, dict):
        return (step.get("title") or step.get("caption") or step.get("line") or "").strip().lower()
    return str(step).strip().lower()


def _take_unique_strings(pool: List[str], n: int, extras: Optional[List[str]] = None) -> List[str]:
    """Return up to n unique strings; never clone the last entry to pad."""
    seen = set()
    out: List[str] = []
    for source in (pool, extras or GENERIC_FALLBACK_STRINGS):
        for s in source:
            key = s.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(s)
            if len(out) >= n:
                return out
    return out


def _detail_differs_from_title(title: str, detail: str) -> bool:
    t, d = title.strip().lower(), detail.strip().lower()
    return bool(d) and d != t


def make_step_detail(title: str, topic: str = "", index: int = 0) -> str:
    """Concrete one-line benefit when detail is missing or duplicates the headline."""
    pool = _topic_fallback_pool_key(topic) if topic else None
    by_pool = {
        "ai": [
            "Clear structure stops vague AI answers and saves rework.",
            "A/B testing prompts finds what actually works for your task.",
            "A prompt library means you never start from a blank page.",
            "Chaining steps turns one good output into a full workflow.",
            "Weekly reviews compound small wins into better results.",
        ],
        "freelance": [
            "Starting with skills you have removes months of prep time.",
            "One clear offer beats ten vague gigs on every platform.",
            "Fast delivery plus reviews unlock higher-paying clients.",
            "Raising rates after proof of results is easier than you think.",
            "Templates let you deliver in half the time per client.",
        ],
        "coding": [
            "Daily reps build pattern recognition faster than cramming.",
            "Timing builds interview stamina under real pressure.",
            "Reviewing optimal solutions teaches tricks books skip.",
            "Redoing misses without hints exposes real weak spots.",
            "Explaining aloud catches gaps before the interviewer does.",
        ],
        "productivity": [
            "Choosing tomorrow's task tonight removes morning decision fatigue.",
            "Short focus blocks beat long sessions you never start.",
            "A daily review shows wins you'd otherwise forget.",
            "Batching similar work cuts context-switching waste.",
            "One polite no protects hours for work that matters.",
        ],
        "network": [
            "Warm intros work better than cold pitches to strangers.",
            "Thoughtful comments get replies; generic likes do not.",
            "One specific question beats a vague 'pick your brain' ask.",
            "A 48-hour follow-up shows you are serious, not spammy.",
            "Giving value first makes later asks feel natural.",
        ],
        "career": [
            "Written wins are proof when review season arrives.",
            "Clear targets turn vague feedback into a real plan.",
            "Booking the review early avoids calendar surprises.",
            "Numbers and quotes make your impact impossible to ignore.",
            "Rehearsing once removes ums and rambling in the room.",
        ],
        "learning": [
            "Short daily blocks beat weekend cramming every time.",
            "Tiny shipped projects teach more than endless tutorials.",
            "Teaching aloud exposes gaps reading alone hides.",
            "Self-quizzes reveal what you only thought you knew.",
            "A Friday ship habit turns learning into visible proof.",
        ],
    }
    if pool and pool in by_pool:
        opts = by_pool[pool]
        return opts[index % len(opts)]

    generic = [
        "Most beginners skip this — doing it today gives you a real edge.",
        "One small action beats reading ten more articles about the topic.",
        "You'll feel the difference the same day you try it once.",
        "This removes the biggest blocker people hit on step one.",
        "Stack it with the previous tip and results compound fast.",
    ]
    return generic[index % len(generic)]


def enrich_step_details(steps: List[Dict], topic: str = "") -> List[Dict]:
    """Ensure each step has a detail line that adds info beyond the title."""
    emojis = SLIDE_EMOJIS
    out = []
    for i, step in enumerate(steps):
        row = dict(step)
        title = (
            row.get("title") or row.get("caption") or row.get("line") or f"Step {i + 1}"
        ).strip()
        detail = (row.get("detail") or "").strip()
        line = (row.get("line") or "").strip()
        if not _detail_differs_from_title(title, detail) and _detail_differs_from_title(title, line):
            detail = line
        if not _detail_differs_from_title(title, detail):
            detail = make_step_detail(title, topic, i)
            row["detail"] = detail
            row["line"] = detail
        if not row.get("emoji"):
            row["emoji"] = emojis[(i + 1) % len(emojis)]
        voice = (row.get("voice") or "").strip()
        if not voice or voice.lower() == title.lower():
            row["voice"] = f"{title}. {detail}"
        out.append(row)
    return out


def _strings_to_step_rows(steps: List[str], topic: str = "") -> List[Dict]:
    rows = []
    for i, s in enumerate(steps):
        detail = make_step_detail(s, topic, i)
        rows.append({
            "title": s,
            "detail": detail,
            "caption": s,
            "line": detail,
            "voice": f"Step {i + 1}: {s}. {detail}",
        })
    return enrich_step_details(rows, topic)


def _topic_has_keywords(t: str, keywords: tuple) -> bool:
    """Match keywords; short tokens like 'ai' use word boundaries to avoid false hits."""
    for k in keywords:
        if k == "ai":
            if re.search(r"\bai\b", t):
                return True
        elif k in t:
            return True
    return False


# More specific topics first — e.g. "side hustles with AI" → freelance, not prompting.
_TOPIC_POOL_MATCH_RULES = (
    ("coding", ("cod", "interview", "leetcode", "algorithm")),
    ("network", ("network", "connect", "linkedin")),
    ("career", ("promot", "raise", "salary", "job", "career")),
    ("learning", ("learn", "skill", "study", "python", "data")),
    ("productivity", ("product", "focus", "habit", "morning", "time")),
    ("freelance", ("freelan", "hustle", "side hustle", "side", "income", "money")),
    ("ai", ("chatgpt", "prompt", "tool", "ai")),
)


def _topic_fallback_pool_key(topic: str) -> Optional[str]:
    t = topic.lower()
    for pool_key, keywords in _TOPIC_POOL_MATCH_RULES:
        if _topic_has_keywords(t, keywords):
            return pool_key
    return None


def topic_fallback_string_pool(topic: str) -> List[str]:
    key = _topic_fallback_pool_key(topic)
    if key:
        return list(FALLBACK_STRING_POOLS[key])
    return list(GENERIC_FALLBACK_STRINGS)


def dedupe_step_rows(steps: List[Dict], alternates: Optional[List[Dict]] = None) -> List[Dict]:
    """Replace duplicate step titles using alternates from the topic pool."""
    seen = set()
    result: List[Dict] = []
    alt = list(alternates or [])
    alt_i = 0
    for step in steps:
        row = dict(step) if isinstance(step, dict) else {
            "title": str(step),
            "detail": str(step),
            "caption": str(step),
            "line": str(step),
            "voice": f"Step {len(result) + 1}: {step}",
        }
        key = _step_title_key(row)
        if key and key in seen:
            replaced = False
            while alt_i < len(alt):
                cand = dict(alt[alt_i])
                alt_i += 1
                ck = _step_title_key(cand)
                if ck and ck not in seen:
                    row = cand
                    key = ck
                    replaced = True
                    break
            if not replaced:
                n = len(result) + 1
                row = {
                    "title": f"Tip {n}",
                    "detail": "Apply one small action from this topic today.",
                    "caption": f"Tip {n}",
                    "line": "Apply one small action from this topic today.",
                    "voice": f"Tip {n}. Apply one small action from this topic today.",
                }
                key = _step_title_key(row)
        if key:
            seen.add(key)
        result.append(row)
    return result


def ensure_tip_steps(tip: Dict, topic: Optional[str] = None) -> Dict:
    """Pad or trim steps so video matches topic count (e.g. 5 tips, not 3)."""
    topic = (topic or tip.get("queue_topic") or tip.get("tip_title") or "").strip()
    n = parse_step_count(topic, tip)
    steps = list(tip.get("steps") or [])

    if len(steps) < n and topic:
        extra = TipGenerator._build_extra_steps(topic, steps, n)
        steps.extend(extra)

    while len(steps) < n:
        i = len(steps)
        steps.append({
            "title": f"Tip {i + 1}",
            "detail": "Apply this step today for faster results.",
            "caption": f"Tip {i + 1}",
            "line": "Apply this step today for faster results.",
            "voice": f"Tip {i + 1}. Apply this step today for faster results.",
        })

    steps = steps[:n]
    if topic:
        alt_strings = _take_unique_strings(topic_fallback_string_pool(topic), n)
        alternates = _strings_to_step_rows(alt_strings, topic)
        steps = dedupe_step_rows(steps, alternates)
    else:
        steps = dedupe_step_rows(steps)

    tip["steps"] = enrich_step_details(steps, topic)
    tip["step_count"] = n
    tip["hook_subtitle"] = tip.get("hook_subtitle") or f"Watch all {n} tips in this Short"
    return tip


_GENERIC_CTAS = {
    "save this and try it today",
    "save this for later",
    "save this",
}


def apply_priority_fixes(tip: Dict, topic: Optional[str] = None) -> Dict:
    """
    Single entry point for all priority content fixes before video build:
    1. Correct step count with unique steps (no clones)
    2. Topic-specific template routing (side hustle before generic AI)
    3. Unique detail / WHY IT MATTERS text (never a copy of the headline)
    4. Topic-specific CTA line
    """
    topic = (topic or tip.get("queue_topic") or tip.get("tip_title") or "").strip()
    tip = ensure_tip_steps(tip, topic)
    n = parse_step_count(topic, tip)
    steps = list(tip.get("steps") or [])
    seen_titles: set = set()
    seen_details: set = set()
    fixes: List[str] = []

    for i, step in enumerate(steps):
        row = dict(step)
        title = (
            row.get("title") or row.get("caption") or row.get("line") or f"Step {i + 1}"
        ).strip()
        tkey = title.lower()
        detail = (row.get("detail") or "").strip()
        line = (row.get("line") or "").strip()
        if not _detail_differs_from_title(title, detail) and _detail_differs_from_title(title, line):
            detail = line

        if tkey in seen_titles:
            pool = topic_fallback_string_pool(topic)
            for alt_title in pool:
                if alt_title.lower() not in seen_titles:
                    title = alt_title
                    tkey = title.lower()
                    detail = make_step_detail(title, topic, i)
                    fixes.append(f"step {i + 1}: duplicate title")
                    break

        if not _detail_differs_from_title(title, detail):
            detail = make_step_detail(title, topic, i)
            fixes.append(f"step {i + 1}: detail matched title")

        dkey = detail.lower()
        if dkey in seen_details:
            detail = make_step_detail(title, topic, i + 3)
            fixes.append(f"step {i + 1}: duplicate detail")

        row["title"] = title
        row["detail"] = detail
        row["line"] = detail
        if not (row.get("voice") or "").strip() or row["voice"].strip().lower() == title.lower():
            row["voice"] = f"{title}. {detail}"
        seen_titles.add(tkey)
        seen_details.add(detail.lower())
        steps[i] = row

    tip["steps"] = enrich_step_details(steps, topic)
    tip["step_count"] = n

    cta = (tip.get("cta_line1") or "").strip()
    if not cta or cta.lower() in _GENERIC_CTAS:
        short = topic.rstrip("?")[:48] if topic else "this topic"
        tip["cta_line1"] = f"Save these {n} tips on {short}"
        fixes.append("cta: topic-specific line")

    if fixes:
        print(f"[TipGenerator] Priority fixes applied: {', '.join(fixes)}")

    return tip

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

    @staticmethod
    def _build_extra_steps(topic: str, existing: List[Dict], need: int) -> List[Dict]:
        """Build missing steps when AI returned fewer than the topic number."""
        have = len(existing)
        seen = {_step_title_key(s) for s in existing if _step_title_key(s)}
        n = parse_step_count(topic)
        pool_key = _topic_fallback_pool_key(topic)
        if pool_key:
            strings = _take_unique_strings(
                FALLBACK_STRING_POOLS[pool_key], n, GENERIC_FALLBACK_STRINGS,
            )
            pool = _strings_to_step_rows(strings, topic)
        else:
            fb = TipGenerator()._fallback_tip(topic)
            pool = fb.get("steps") or []
        out = []
        for step in pool:
            if len(existing) + len(out) >= need:
                break
            key = _step_title_key(step)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            out.append(dict(step))
        while len(existing) + len(out) < need:
            i = len(existing) + len(out)
            out.append({
                "title": f"Tip {i + 1}",
                "detail": "One more key action from this topic.",
                "voice": f"Tip {i + 1}. One more key action from this topic.",
                "line": "One more key action from this topic.",
                "caption": f"Tip {i + 1}",
            })
        return out

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
        Fallback that generates topic-relevant steps from the topic string itself.
        (Used when Gemini quota is exceeded / API fails.)
        """
        if topic:
            title = topic.strip().rstrip("?")[:60]
            hook = topic.strip()[:80]
            t = topic.lower()

            # Topic-aware step templates (pools have 5+ unique lines; padding never clones)
            pool_key = _topic_fallback_pool_key(topic)
            if pool_key:
                n = parse_step_count(topic)
                steps = _take_unique_strings(
                    FALLBACK_STRING_POOLS[pool_key], n, GENERIC_FALLBACK_STRINGS,
                )
                step_rows = _strings_to_step_rows(steps, topic)
            elif re.search(r"\b(apps?|tools?|software|platforms?)\b", t):
                n = parse_step_count(topic)
                pool = [
                    ("Notion AI", "Notes, tasks, and AI writing in one workspace"),
                    ("Todoist", "Smart to-do lists with quick natural input"),
                    ("Otter.ai", "Records calls and auto-writes meeting notes"),
                    ("Calendly", "Books meetings without endless email threads"),
                    ("Zapier", "Links your apps so busywork runs itself"),
                    ("Grammarly", "Fixes grammar and tone while you type"),
                    ("Reclaim.ai", "Auto-blocks focus time on your calendar"),
                ]
                step_dicts = []
                for i in range(n):
                    name, detail = pool[i % len(pool)]
                    step_dicts.append({
                        "title": name,
                        "detail": detail,
                        "caption": name,
                        "line": detail,
                        "voice": f"App {i + 1}: {name}. {detail}",
                    })
                step_rows = step_dicts
            else:
                n = parse_step_count(topic)
                words = [w for w in title.split() if len(w) > 3][:3]
                noun = words[0].capitalize() if words else "this"
                templates = [
                    (f"Start with one {noun} habit", f"Pick the smallest action you can do in five minutes"),
                    (f"Build a daily {noun} routine", f"Repeat at the same time so your brain expects it"),
                    (f"Track your {noun} results", f"Write one win each day so progress stays visible"),
                    (f"Remove one {noun} blocker", f"Delete or automate the task that slows you down"),
                    (f"Share one {noun} lesson", f"Teaching others locks in what you learned"),
                ]
                step_rows = [
                    {"title": t[0], "detail": t[1], "caption": t[0], "line": t[1],
                     "voice": f"Step {i + 1}: {t[0]}. {t[1]}"}
                    for i, t in enumerate(templates[:n])
                ]

            step_rows = step_rows[: parse_step_count(topic)]
            n = len(step_rows)
            tip = {
                "slide_emojis": SLIDE_EMOJIS,
                "hook": hook[:80],
                "hook_voice": hook[:80],
                "hook_subtitle": f"Watch all {n} tips in 30 seconds",
                "tip_title": title[:60],
                "step_count": n,
                "steps": step_rows,
                "cta_line1": "Save this and try it today",
                "cta_line2": "Comment 'DONE' when you try it!",
                "cta_voice": "Save this and try it today. Comment DONE when you try it!",
                "script": (
                    f"{hook}. "
                    + " ".join(
                        s["voice"] if isinstance(s, dict) else s
                        for s in step_rows
                    )
                    + " Save this and try it today. Comment DONE when you try it!"
                ),
                "suggested_titles": [f"{title[:55]} #Shorts"],
                "suggested_description": (
                    f"{topic}\n\n"
                    f"Daily {self.niche} tips in English. Follow {CHANNEL_NAME} for more."
                ),
                "tags": ["#shorts", "#tips", "#productivity"],
                "hot_words": [w for w in title.lower().split() if len(w) > 3][:6],
                "main_topic": "Education",
                "source": "fallback",
                "niche": self.niche,
                "queue_topic": topic,
            }
            return ensure_tip_steps(tip, topic)

        # Non-topic fallback (static examples, kept for compatibility)
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

        step_n = parse_step_count(topic)
        if topic:
            focus = f"""TOPIC (center the entire Short on this — hook must mention it):
"{topic}"
Niche context: {self.niche}
Create exactly {step_n} steps that directly answer this topic (e.g. if topic says "5 apps", list 5 real app names).
Each step needs DIFFERENT fields:
- title: short headline only (max 6 words, e.g. app name)
- detail: one sentence explaining it (max 14 words, must NOT repeat title)
- voice: spoken line for TTS (title + detail, max 18 words)
Do NOT put the same text in title and detail."""
        else:
            focus = f"Niche: {self.niche}"

        prompt = f"""Create ONE English YouTube Short.
{focus}

Return ONLY valid JSON (no markdown).

RULES:
- slide_emojis: ["📧","📤","📂","⏱️","💾"]
- step_count: {step_n}
- hook and hook_voice: identical (max 12 words)
- hook_subtitle: teaser only, e.g. "All 5 tips in 30 seconds" — do NOT list step names on hook
- Each step: title (headline), detail (explanation), voice (spoken). title and detail MUST differ.
- cta_line1: short, generic, topic-relevant (max 10 words). Examples:
  - "Save this and try it today"
  - "Save this for your next interview"
- cta_line2: "Comment 'DONE' when you try it!"
- cta_voice: speak cta_line1 then cta_line2 word-for-word (no extra words)
- Exactly {step_n} logical connected steps. Avoid: {avoid_str}

{{
  "slide_emojis": ["📧","📤","📂","⏱️","💾"],
  "step_count": {step_n},
  "hook": "Same text as hook_voice",
  "hook_voice": "Same text as hook",
  "hook_subtitle": "Short teaser, no step spoilers",
  "tip_title": "Internal title",
  "steps": [
    {{"title":"Headline","detail":"Different explanation sentence","voice":"Spoken title and detail","line":"same as detail"}}
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
                tip["on_screen_lines"] = [s.get("line", "") for s in tip["steps"]]
            tip = ensure_tip_steps(tip, topic)
            self._save_history(tip)
            return tip
        except Exception as e:
            print(f"[TipGenerator] Gemini failed ({e}), using fallback tip")
            tip = self._fallback_tip(topic=topic)
            tip["generated_on"] = date.today().isoformat()
            tip = ensure_tip_steps(tip, topic)
            self._save_history(tip)
            return tip

    def save_tip_json(self, tip: Dict, output_dir: Optional[str] = None) -> str:
        folder = Path(output_dir or QUEUE_OUTPUT_FOLDER)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"tip_{date.today().isoformat()}_{self._tip_hash(tip)}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tip, f, indent=2)
        return str(path)
