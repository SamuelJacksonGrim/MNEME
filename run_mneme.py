#!/usr/bin/env python3
"""Execute the MNEME self-reinforcement loop and emit a generation report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loop import MnemeLoop


def main() -> None:
    mem = Path("/tmp/mneme_memory")
    mem.mkdir(parents=True, exist_ok=True)
    ledger = mem / "ledger.jsonl"
    if ledger.exists():
        ledger.unlink()
    loop = MnemeLoop(ledger)
    state = loop.run(generations=8)

    print("=" * 72)
    print("MNEME  //  self-reinforcement training loop")
    print("The memories of the past become food for the future.")
    print("=" * 72)
    for r in state.reports:
        s = r.stats
        e = r.emergent
        print(
            f"\nGEN {r.generation:02d}  "
            f"n={s['n']}  success={s['success_rate']:.2f}  "
            f"composite={s['mean_composite']:.3f}  collapse={s['mean_collapse']:.3f}"
        )
        print(f"  gate: {'OPEN' if r.accepted_update else 'CLOSED'} — {r.gate_reason}")
        if e:
            print(
                "  emergence  "
                f"verify={e['verification']:.2f}  "
                f"backtrack={e['backtracking']:.2f}  "
                f"subgoal={e['subgoal_setting']:.2f}  "
                f"backchain={e['backward_chaining']:.2f}"
            )
    if state.halted:
        print(f"\nHALT: {state.halt_reason}")

    summary = {
        "generations": [
            {
                "generation": r.generation,
                "stats": r.stats,
                "accepted_update": r.accepted_update,
                "gate_reason": r.gate_reason,
                "emergent": r.emergent,
            }
            for r in state.reports
        ],
        "halted": state.halted,
        "halt_reason": state.halt_reason,
        "ledger": str(ledger),
        "episodes": len(loop.ledger.all()),
    }
    out = mem / "report.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nledger → {ledger}")
    print(f"report → {out}")
    print(f"episodes written: {summary['episodes']}")


if __name__ == "__main__":
    main()
