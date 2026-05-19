"""
Content queue: read video topics from a text file (one per line),
pick a random unused line, track progress so lines are not repeated.
"""
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import CONTENT_QUEUE_FILE


class ContentQueue:
    """Manage a line-based topic file and which lines were already used."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        state_path: Optional[str] = None,
    ):
        self.file_path = Path(file_path or CONTENT_QUEUE_FILE)
        self.state_path = Path(
            state_path or self.file_path.parent / ".content_queue_state.json"
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_lines(self) -> List[str]:
        """Load non-empty, non-comment lines from the topic file."""
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Content file not found: {self.file_path}\n"
                f"Create it with one topic per line (e.g. questions for Shorts)."
            )
        lines: List[str] = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
        if not lines:
            raise ValueError(f"No topics in {self.file_path} (add one topic per line).")
        return lines

    def _load_state(self) -> Dict:
        if not self.state_path.exists():
            return {"used_indices": [], "history": []}
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("used_indices", [])
            data.setdefault("history", [])
            return data
        except Exception:
            return {"used_indices": [], "history": []}

    def _save_state(self, state: Dict) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def unused_indices(self) -> List[int]:
        lines = self.load_lines()
        used = set(self._load_state().get("used_indices", []))
        return [i for i in range(len(lines)) if i not in used]

    def pick_random_line(self, reset_if_exhausted: bool = True) -> Tuple[int, str]:
        """
        Pick a random unused line. Returns (index, topic_text).
        If all lines were used and reset_if_exhausted, clears used list and picks again.
        """
        lines = self.load_lines()
        unused = self.unused_indices()

        if not unused:
            if reset_if_exhausted:
                print("[ContentQueue] All topics used — resetting queue for a new cycle.")
                state = self._load_state()
                state["used_indices"] = []
                self._save_state(state)
                unused = list(range(len(lines)))
            else:
                raise RuntimeError(
                    "All topics in the content file have been used. "
                    "Add more lines to the file or delete .content_queue_state.json to reset."
                )

        index = random.choice(unused)
        return index, lines[index]

    def mark_used(self, index: int, topic: str, video_path: str = "") -> None:
        state = self._load_state()
        used = state.setdefault("used_indices", [])
        if index not in used:
            used.append(index)
        from datetime import datetime

        state.setdefault("history", []).append({
            "index": index,
            "topic": topic,
            "video_path": video_path,
            "used_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        state["history"] = state["history"][-200:]
        self._save_state(state)

    def status(self) -> Dict:
        lines = self.load_lines()
        unused = self.unused_indices()
        return {
            "file": str(self.file_path),
            "total": len(lines),
            "used": len(lines) - len(unused),
            "remaining": len(unused),
            "lines": lines,
            "unused_indices": unused,
        }

    def reset(self) -> None:
        """Clear used-line tracking (start over)."""
        self._save_state({"used_indices": [], "history": []})
