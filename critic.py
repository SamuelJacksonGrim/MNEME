"""Separate critic. The actor reasons. The critic scores. Separation is the anti-hack."""

from __future__ import annotations

import re
from collections import Counter

from schema import CognitiveBehaviors, CoTStep, MetricVector, Outcome

VERIFY_MARKERS = (
    "check", "verify", "confirm", "does this hold", "recompute", "validate", "test against"
)
BACKTRACK_MARKERS = (
    "that fails", "wrong path", "abandon", "try another", "retract", "does not work", "backtrack"
)
SUBGOAL_MARKERS = (
    "first,", "subgoal", "break into", "step 1", "decompose", "part a", "intermediate"
)
BACKCHAIN_MARKERS = (
    "working backward", "from the goal", "must therefore", "required that", "implies prior"
)


def _presence(text: str, markers: tuple[str, ...]) -> float:
    t = text.lower()
    hits = sum(1 for m in markers if m in t)
    return min(1.0, hits / 2.0)


def score_behaviors(steps: list[CoTStep]) -> CognitiveBehaviors:
    text = " ".join(s.thought for s in steps)
    discarded = sum(1 for s in steps if s.discarded)
    verification = _presence(text, VERIFY_MARKERS)
    backtracking = min(1.0, _presence(text, BACKTRACK_MARKERS) + 0.35 * min(1, discarded))
    subgoal_setting = _presence(text, SUBGOAL_MARKERS)
    backward_chaining = _presence(text, BACKCHAIN_MARKERS)
    kinds = {s.kind for s in steps}
    if "verify" in kinds:
        verification = max(verification, 0.6)
    if "backtrack" in kinds:
        backtracking = max(backtracking, 0.7)
    if "subgoal" in kinds:
        subgoal_setting = max(subgoal_setting, 0.6)
    if "backchain" in kinds:
        backward_chaining = max(backward_chaining, 0.6)
    return CognitiveBehaviors(
        verification=verification,
        backtracking=backtracking,
        subgoal_setting=subgoal_setting,
        backward_chaining=backward_chaining,
    )


def score_coherence(steps: list[CoTStep]) -> float:
    if not steps:
        return 0.0
    kinds = [s.kind for s in steps]
    order_bonus = 0.0
    expected = ["perceive", "subgoal", "hypothesize", "verify", "conclude"]
    idx = 0
    for k in kinds:
        if idx < len(expected) and k == expected[idx]:
            idx += 1
            order_bonus += 0.12
    conf_mean = sum(s.confidence for s in steps) / len(steps)
    length_pen = 0.0 if 3 <= len(steps) <= 14 else 0.2
    return max(0.0, min(1.0, 0.4 + order_bonus + 0.3 * conf_mean - length_pen))


def score_novelty(answer: str, prior_answers: list[str]) -> float:
    if not prior_answers:
        return 0.6
    a = answer.strip().lower()
    same = sum(1 for p in prior_answers if p.strip().lower() == a)
    ratio = same / max(1, len(prior_answers))
    return max(0.0, 1.0 - ratio)


def score_collapse(answer: str, steps: list[CoTStep], prior_answers: list[str]) -> float:
    risk = 0.0
    if prior_answers:
        c = Counter(p.strip().lower() for p in prior_answers[-12:])
        if c and c.most_common(1)[0][1] >= 6 and answer.strip().lower() == c.most_common(1)[0][0]:
            risk += 0.55
    if len(steps) <= 1:
        risk += 0.25
    text = " ".join(s.thought for s in steps)
    if re.search(r"^(answer is|final:)\s", text.lower()):
        risk += 0.15
    template_hits = sum(1 for s in steps if s.thought.strip().lower() in {
        "consider the problem", "think step by step", "therefore the answer"
    })
    if template_hits >= 2:
        risk += 0.2
    return min(1.0, risk)


def score_efficiency(steps: list[CoTStep], correct: bool) -> float:
    n = len(steps)
    if correct and n <= 8:
        return 0.85
    if correct:
        return max(0.3, 1.0 - 0.05 * (n - 8))
    return max(0.1, 0.5 - 0.03 * n)


def critique(answer, gold, steps, prior_answers):
    correct = False
    if gold is not None:
        correct = _normalize(answer) == _normalize(gold)
    behaviors = score_behaviors(steps)
    coherence = score_coherence(steps)
    novelty = score_novelty(answer, prior_answers)
    collapse = score_collapse(answer, steps, prior_answers)
    efficiency = score_efficiency(steps, correct)
    process = min(1.0, 0.5 * coherence + 0.5 * behaviors.mean())
    metrics = MetricVector(
        correctness=1.0 if correct else (0.35 if gold is None else 0.0),
        cot_coherence=coherence,
        process_fidelity=process,
        novelty=novelty,
        efficiency=efficiency,
        collapse_risk=collapse,
        behaviors=behaviors,
    )
    lessons = []
    if not correct and gold is not None:
        lessons.append(f"Failure signature: produced '{answer}' against gold '{gold}'.")
        discarded = [s.thought for s in steps if s.discarded]
        if discarded:
            lessons.append("Abandoned paths: " + " | ".join(discarded[:3]))
        if behaviors.verification < 0.3:
            lessons.append("Missing verification before commit.")
        if behaviors.backtracking < 0.3 and not correct:
            lessons.append("No backtrack after inconsistency.")
        if behaviors.subgoal_setting < 0.3:
            lessons.append("Did not decompose; jumped to conclusion.")
    if correct and behaviors.mean() < 0.25:
        lessons.append("Correct by accident. Do not reinforce shallow traces.")
        metrics.correctness *= 0.7
        metrics.process_fidelity *= 0.6
    if collapse > 0.4:
        lessons.append("Collapse risk: answer pattern repeating. Force novelty.")
    if correct and metrics.composite() >= 0.55:
        outcome = Outcome.SUCCESS
    elif correct:
        outcome = Outcome.PARTIAL
    elif gold is None and metrics.composite() >= 0.5:
        outcome = Outcome.PARTIAL
    else:
        outcome = Outcome.FAILURE
    return outcome, metrics, lessons


def _normalize(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\-\.\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s
