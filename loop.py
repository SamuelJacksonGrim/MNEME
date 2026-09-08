"""MNEME self-reinforcement loop.

Perceive → Retrieve past traces → CoT reason → Critique with
success/failure vectors → Write memory → Update policy under a
Lyapunov-style gate → Repeat.

The memories of the past become food for the future.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from critic import critique
from ledger import MemoryLedger
from reasoner import Policy, Reasoner, render_memory_context
from schema import Episode
from tasks import curriculum_for_generation


@dataclass
class GenerationReport:
    generation: int
    stats: dict
    accepted_update: bool
    gate_reason: str
    emergent: dict


@dataclass
class LoopState:
    generation: int = 0
    reports: list[GenerationReport] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""


class LyapunovGate:
    """Accept a policy update only if competence rose or collapse fell
    without a catastrophic competence drop. Shadows of RFE / E8-EEA."""

    def __init__(self, min_delta: float = -0.04, collapse_ceiling: float = 0.55):
        self.min_delta = min_delta
        self.collapse_ceiling = collapse_ceiling
        self.prev_composite = 0.0
        self.prev_collapse = 1.0
        self.armed = False

    def allow(self, composite: float, collapse: float) -> tuple[bool, str]:
        if not self.armed:
            self.armed = True
            self.prev_composite = composite
            self.prev_collapse = collapse
            return True, "first generation: seed the ledger"
        delta = composite - self.prev_composite
        if collapse >= self.collapse_ceiling and collapse > self.prev_collapse:
            return False, "gate closed: collapse rising through ceiling"
        if delta < self.min_delta and collapse >= self.prev_collapse:
            return False, f"gate closed: competence Δ={delta:.3f} with no collapse relief"
        self.prev_composite = max(self.prev_composite * 0.3 + composite * 0.7, composite * 0.85)
        self.prev_collapse = collapse
        return True, f"gate open: Δcomposite={delta:.3f} collapse={collapse:.3f}"


class MnemeLoop:
    def __init__(self, ledger_path: str | Path, k_retrieve: int = 5):
        self.ledger = MemoryLedger(ledger_path)
        self.policy = Policy()
        self.reasoner = Reasoner(self.policy)
        self.gate = LyapunovGate()
        self.state = LoopState()
        self.k = k_retrieve

    def run(self, generations: int = 8) -> LoopState:
        for g in range(generations):
            self.state.generation = g
            self._run_generation(g)
            if self.state.halted:
                break
        return self.state

    def _run_generation(self, g: int) -> None:
        tasks = curriculum_for_generation(g)
        prior_answers = [e.answer for e in self.ledger.all()]

        for task in tasks:
            retrieved = self.ledger.retrieve(task.prompt, k=self.k)
            ctx = render_memory_context(retrieved)
            steps, answer = self.reasoner.solve(task, ctx)
            outcome, metrics, lessons = critique(answer, task.gold, steps, prior_answers)
            ep = Episode(
                task_id=task.task_id,
                prompt=task.prompt,
                generation=g,
                steps=steps,
                answer=answer,
                gold=task.gold,
                outcome=outcome,
                metrics=metrics,
                lessons=lessons,
                retrieved_ids=[e.episode_id for e in retrieved],
            )
            self.ledger.append(ep)
            prior_answers.append(answer)
            if outcome.value == "failure":
                self.policy.banned_answers.add(answer.lower())

        self.ledger.flush()
        stats = self.ledger.generation_stats(g)
        accepted, reason = self.gate.allow(stats["mean_composite"], stats["mean_collapse"])
        if accepted:
            self.policy.digest(
                self.ledger.export_lessons(),
                stats["success_rate"],
                stats["mean_collapse"],
            )
            self.reasoner.policy = self.policy
        else:
            self.state.halted = stats["mean_collapse"] >= 0.7
            self.state.halt_reason = reason

        emergent = self._emergence(g)
        self.state.reports.append(GenerationReport(
            generation=g,
            stats=stats,
            accepted_update=accepted,
            gate_reason=reason,
            emergent=emergent,
        ))

    def _emergence(self, g: int) -> dict:
        eps = self.ledger.by_generation(g)
        if not eps:
            return {}
        return {
            "verification": sum(e.metrics.behaviors.verification for e in eps) / len(eps),
            "backtracking": sum(e.metrics.behaviors.backtracking for e in eps) / len(eps),
            "subgoal_setting": sum(e.metrics.behaviors.subgoal_setting for e in eps) / len(eps),
            "backward_chaining": sum(e.metrics.behaviors.backward_chaining for e in eps) / len(eps),
        }
