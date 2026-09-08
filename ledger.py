"""Persistent memory ledger. Past traces are ingested, ranked, and retrieved as food."""

from __future__ import annotations

import json
from pathlib import Path

from schema import Episode, Outcome, episode_from_dict


class MemoryLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._episodes: list[Episode] = []
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self._episodes.append(episode_from_dict(json.loads(line)))
            except json.JSONDecodeError:
                continue

    def append(self, episode: Episode) -> None:
        self._episodes.append(episode)

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(e.as_dict(), ensure_ascii=False) for e in self._episodes]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def all(self) -> list[Episode]:
        return list(self._episodes)

    def by_generation(self, gen: int) -> list[Episode]:
        return [e for e in self._episodes if e.generation == gen]

    def retrieve(self, prompt: str, k: int = 5) -> list[Episode]:
        """Retrieve useful past: high composite successes + instructive failures."""
        if not self._episodes:
            return []
        scored: list[tuple[float, Episode]] = []
        tokens = set(prompt.lower().split())
        for ep in self._episodes:
            overlap = len(tokens & set(ep.prompt.lower().split()))
            relatedness = overlap / max(1, len(tokens))
            quality = ep.metrics.composite()
            failure_value = 0.25 if ep.outcome == Outcome.FAILURE and ep.lessons else 0.0
            score = 0.45 * relatedness + 0.40 * quality + 0.15 * failure_value
            score += 0.02 * min(ep.generation, 20)
            scored.append((score, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked: list[Episode] = []
        seen = set()
        for _, ep in scored:
            if ep.episode_id in seen:
                continue
            picked.append(ep)
            seen.add(ep.episode_id)
            if len(picked) >= k:
                break
        failures = [e for e in self._episodes if e.outcome == Outcome.FAILURE and e.lessons]
        if failures and not any(e.outcome == Outcome.FAILURE for e in picked) and picked:
            picked[-1] = failures[-1]
        return picked

    def generation_stats(self, gen: int) -> dict:
        eps = self.by_generation(gen)
        if not eps:
            return {
                "n": 0,
                "success_rate": 0.0,
                "mean_composite": 0.0,
                "mean_behaviors": 0.0,
                "mean_collapse": 0.0,
                "mean_correctness": 0.0,
            }
        succ = sum(1 for e in eps if e.outcome == Outcome.SUCCESS)
        return {
            "n": len(eps),
            "success_rate": succ / len(eps),
            "mean_composite": sum(e.metrics.composite() for e in eps) / len(eps),
            "mean_behaviors": sum(e.metrics.behaviors.mean() for e in eps) / len(eps),
            "mean_collapse": sum(e.metrics.collapse_risk for e in eps) / len(eps),
            "mean_correctness": sum(e.metrics.correctness for e in eps) / len(eps),
        }

    def export_lessons(self, limit: int = 12) -> list[str]:
        lessons: list[str] = []
        for ep in reversed(self._episodes):
            for lesson in ep.lessons:
                if lesson not in lessons:
                    lessons.append(lesson)
                if len(lessons) >= limit:
                    return lessons
        return lessons
