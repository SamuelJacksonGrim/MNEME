# MNEME

**The memories of the past become food for the future.**

Self-reinforcing Chain-of-Thought training loop. Success and failure are
not discarded labels. They are a metric vector written into a ledger,
retrieved as context, and digested into the next policy. CoT is the
policy-improvement operator. A Lyapunov-style gate decides whether the
update is allowed to land.

Experimental subsystem. It is meant to **run on top of** the other family
engines — RFE-Core / RFE-Core2, E8-EEA, Liminal Anchor Engine, Paradox
Lattice — not replace them.

Repo: https://github.com/SamuelJacksonGrim/MNEME

## Loop

```
task  →  retrieve ledger traces
      →  CoT (perceive → subgoal → retrieve → backchain → hypothesize
              → verify → backtrack-if-needed → conclude)
      →  critic scores a MetricVector
      →  lessons written
      →  episode appended to ledger
      →  generation stats
      →  Lyapunov gate
      →  policy digest (only if gate opens)
      →  next generation, harder curriculum
```

## Metric vector

| Axis | Role |
|---|---|
| `correctness` | Outcome against gold. Discounted if the trace is shallow. |
| `cot_coherence` | Ordered reasoning, not a template dump. |
| `process_fidelity` | Did the chain do the work? |
| `novelty` | Penalty for repeating the same answer surface. |
| `efficiency` | Correctness with bounded length. |
| `collapse_risk` | Template collapse / self-reward hacking detector. |
| `behaviors` | Verification, backtracking, subgoal setting, backward chaining. |

Composite competence is Lyapunov-aware: competence minus instability.

Correct answers produced by empty process are treated as *partial*, not
success. Accident is not intelligence. Do not reinforce it.

## Why failures are kept

Error avalanching is the known death of self-training. MNEME does the
opposite of hiding failure:

- Failures generate lessons.
- Lessons are retrieved into the next CoT as explicit warnings.
- Failed answers can be banned by the collapse guard.
- The critic is a separate organ from the actor.

## Gate

An update is refused when collapse rises through its ceiling, or when
competence falls without collapse relief. Memory still writes. Policy
freezes.

## Run

Python 3.10+, no third-party dependencies.

```bash
python3 run_mneme.py
```

Writes generation output under `/tmp/mneme_memory/` by default.

## Bindings

- **RFE / E8-EEA** — consume `MetricVector` and gate decisions as recursion fuel.
- **Gemini** — counter-intrusion prior from collapse_risk and banned answers.
- **Sentinel** — live threat gauge on collapse_risk.
- **Hephaestus** — ledger as a component test harness.

## License

Dual license: **AGPL-3.0-or-later OR Apache-2.0**.

See `LICENSE`, `LICENSE-AGPL-3.0`, and `LICENSE-APACHE-2.0`.

Copyright 2026 Samuel Jackson Grim.
