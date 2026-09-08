"""Curriculum of reasoning tasks. Difficulty climbs as the loop eats its own past."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt: str
    gold: str
    domain: str
    difficulty: int
    hints: tuple[str, ...] = ()


CURRICULUM: list[Task] = [
    Task(
        "arith.01",
        "A farmer has 17 sheep. All but 9 run away. How many remain?",
        "9",
        "language-trap",
        1,
        ("Read the sentence literally. 'All but 9' means 9 stay.",),
    ),
    Task(
        "arith.02",
        "What is 3 × (2 + 5) − 4?",
        "17",
        "order-of-operations",
        1,
        ("Parentheses first, then multiply, then subtract.",),
    ),
    Task(
        "logic.01",
        "Every knight always tells the truth. Every knave always lies. A says: 'B is a knave.' B says: 'A and I are both knaves.' What is A and what is B?",
        "A knight, B knave",
        "knights-knaves",
        2,
        ("B cannot be a knight: a knight would not claim both are knaves.",),
    ),
    Task(
        "seq.01",
        "Find the next number: 2, 3, 5, 8, 12, 17, ?",
        "23",
        "sequence",
        2,
        ("Differences: +1,+2,+3,+4,+5. Next difference +6.",),
    ),
    Task(
        "logic.02",
        "Three boxes. One contains gold, one contains stones, one contains gold and stones. Labels: 'gold', 'stones', 'gold and stones'. Every label is false. Which box contains only gold?",
        "stones",
        "false-labels",
        3,
        ("The box labeled 'gold and stones' cannot be mixed; it is pure. Then eliminate.",),
    ),
    Task(
        "count.01",
        "Using 25, 10, 8, 3 exactly once and the operations + − × ÷, make 24.",
        "10-8+25-3",
        "countdown",
        3,
        ("24 can be assembled as a signed sum: 25 + 10 - 8 - 3, or 10 - 8 + 25 - 3.",),
    ),
    Task(
        "causal.01",
        "A man lives on the 10th floor. Every morning he takes the elevator to the ground. When he comes home he takes the elevator to the 7th floor and walks the rest, except on rainy days when he rides to the 10th. Why?",
        "he is too short to reach the 10 button except with an umbrella",
        "insight",
        3,
        ("The exception is rain. What does rain give him that he lacks otherwise?",
    ),
    Task(
        "math.01",
        "A number is multiplied by 4, then 6 is added, then the result is divided by 2, yielding 15. What was the number?",
        "6",
        "backward-algebra",
        2,
        ("Work backward from 15.",),
    ),
    Task(
        "logic.03",
        "If all As are Bs, and some Bs are Cs, does it follow that some As are Cs?",
        "no",
        "syllogism",
        2,
        ("Some B being C need not intersect the A subset of B.",),
    ),
    Task(
        "opt.01",
        "You have a 3-liter and a 5-liter jug. How do you measure exactly 4 liters from a lake? Give the shortest sequence of fill/pour/empty actions ending at 4 in the 5-liter jug.",
        "fill5 pour5to3 empty3 pour5to3 fill5 pour5to3",
        "water-jug",
        3,
        ("Classic: 5, pour into 3, empty 3, pour remainder 2 into 3, fill 5, pour 1 into 3, leave 4.",),
    ),
]


def curriculum_for_generation(gen: int) -> list[Task]:
    cap = 1 + min(4, gen // 2)
    return [t for t in CURRICULUM if t.difficulty <= cap]
