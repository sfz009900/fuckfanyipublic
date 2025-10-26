import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SM2State:
    ease: float = 2.5
    interval_sec: int = 0
    reps: int = 0
    lapses: int = 0


def next_review(state: SM2State, grade: int, now: Optional[float] = None) -> SM2State:
    """Compute next review using a simplified SM-2 schedule.

    grade: 0=again, 1=hard, 2=good, 3=easy
    Returns updated state with new interval_sec and ease.
    """
    if now is None:
        now = time.time()

    ease = max(1.3, state.ease)
    reps = state.reps
    lapses = state.lapses

    if grade == 0:  # again
        lapses += 1
        reps = 0
        ease = max(1.3, ease - 0.2)
        interval_sec = 60 * 5  # 5 minutes
    else:
        if reps == 0:
            interval_sec = 60 * 10 if grade == 1 else 60 * 60  # 10m hard, 1h good/easy first pass
        elif reps == 1:
            interval_sec = 60 * 60 * 12  # 12h
        else:
            # Adjust ease
            if grade == 1:
                ease = max(1.3, ease - 0.05)
            elif grade == 3:
                ease = ease + 0.05

            # Interval grows with ease
            interval_sec = int(state.interval_sec * ease)
            # floor to 1 day minimum after first two reps
            interval_sec = max(interval_sec, 60 * 60 * 24)

        reps += 1

    return SM2State(ease=ease, interval_sec=interval_sec, reps=reps, lapses=lapses)
