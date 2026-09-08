"""MNEME metric and episode schema.

Success and failure are not binary flags. They are a vector that
the next generation eats as context, reward, and warning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
import time
import uuid


class Outcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ABORTED = "aborted"


@dataclass
class CognitiveBehaviors:
    """Four habits that enable self-improving reasoners."""

    verification: float = 0.0
    backtracking: float = 0.0
    subgoal_setting: float = 0.0
    backward_chaining: float = 0.0

    def mean(self) -> float:
        return (
            self.verification
            + self.backtracking
            + self.subgoal_setting
            + self.backward_chaining
        ) / 4.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class MetricVector:
    """Previously coded success / failure metrics, now food."""

    correctness: float = 0.0
    cot_coherence: float = 0.0
    process_fidelity: float = 0.0
    novelty: float = 0.0
    efficiency: float = 0.0
    collapse_risk: float = 0.0
    behaviors: CognitiveBehaviors = field(default_factory=CognitiveBehaviors)

    def composite(self) -> float:
        """Lyapunov-aware composite: competence minus instability."""
        competence = (
            0.35 * self.correctness
            + 0.20 * self.cot_coherence
            + 0.20 * self.process_fidelity
            + 0.15 * self.behaviors.mean()
            + 0.10 * self.novelty
        )
        stability_penalty = 0.35 * self.collapse_risk
        efficiency_bonus = 0.08 * self.efficiency
        return max(0.0, min(1.0, competence + efficiency_bonus - stability_penalty))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoTStep:
    kind: str
    thought: str
    confidence: float = 0.5
    discarded: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Episode:
    task_id: str
    prompt: str
    generation: int
    steps: list[CoTStep]
    answer: str
    gold: str | None
    outcome: Outcome
    metrics: MetricVector
    lessons: list[str] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    episode_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "prompt": self.prompt,
            "generation": self.generation,
            "steps": [s.as_dict() for s in self.steps],
            "answer": self.answer,
            "gold": self.gold,
            "outcome": self.outcome.value,
            "metrics": self.metrics.as_dict(),
            "composite": self.metrics.composite(),
            "lessons": self.lessons,
            "retrieved_ids": self.retrieved_ids,
            "ts": self.ts,
        }


def episode_from_dict(d: dict[str, Any]) -> Episode:
    m = d.get("metrics", {})
    b = m.get("behaviors", {})
    behaviors = CognitiveBehaviors(**{k: float(b.get(k, 0.0)) for k in (
        "verification", "backtracking", "subgoal_setting", "backward_chaining"
    )})
    metrics = MetricVector(
        correctness=float(m.get("correctness", 0.0)),
        cot_coherence=float(m.get("cot_coherence", 0.0)),
        process_fidelity=float(m.get("process_fidelity", 0.0)),
        novelty=float(m.get("novelty", 0.0)),
        efficiency=float(m.get("efficiency", 0.0)),
        collapse_risk=float(m.get("collapse_risk", 0.0)),
        behaviors=behaviors,
    )
    steps = [CoTStep(**s) for s in d.get("steps", [])]
    return Episode(
        episode_id=d.get("episode_id", uuid.uuid4().hex[:12]),
        task_id=d["task_id"],
        prompt=d["prompt"],
        generation=int(d.get("generation", 0)),
        steps=steps,
        answer=d.get("answer", ""),
        gold=d.get("gold"),
        outcome=Outcome(d.get("outcome", "failure")),
        metrics=metrics,
        lessons=list(d.get("lessons", [])),
        retrieved_ids=list(d.get("retrieved_ids", [])),
        ts=float(d.get("ts", time.time())),
    )
