import time
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from .capture import CaptureConfig, capture_rate
from .scoring import score_capture
from .constants import SCORE_THRESHOLD


@dataclass
class RateOutcome:
    rate: int
    score: float
    breakdown: object
    silent: bool
    error: str


@dataclass
class AggregateResult:
    rate: int
    hit_rate: float
    avg_score: float
    best_score: float
    best_sample: str


def alternate_order(rates: List[int], cycle_index: int) -> List[int]:
    return list(rates) if cycle_index % 2 == 0 else list(reversed(rates))


def run_cycle(path, rates, cfg: CaptureConfig, on_rate_result: Optional[Callable] = None):
    outcomes = []
    for rate in rates:
        cap = capture_rate(path, rate, cfg)
        if cap.error:
            outcome = RateOutcome(rate=rate, score=0.0, breakdown=None, silent=True, error=cap.error)
        elif cap.silent:
            outcome = RateOutcome(rate=rate, score=0.0, breakdown=None, silent=True, error="")
        else:
            breakdown = score_capture(cap.raw, cap.framing_errors)
            outcome = RateOutcome(rate=rate, score=breakdown.total, breakdown=breakdown, silent=False, error="")
        outcomes.append(outcome)
        if on_rate_result:
            on_rate_result(outcome)
    return outcomes


def run_scan(
    path,
    rates: List[int],
    cfg: CaptureConfig,
    repeat: int = 1,
    threshold: float = SCORE_THRESHOLD,
    deadline: Optional[float] = None,
    on_cycle_start: Optional[Callable] = None,
    on_rate_result: Optional[Callable] = None,
):
    hits = {r: 0 for r in rates}
    scores = {r: [] for r in rates}
    best_sample = {r: "" for r in rates}
    best_score = {r: 0.0 for r in rates}
    cycles_run = 0

    for cycle_index in range(repeat):
        if deadline is not None and time.monotonic() >= deadline:
            break
        ordered = alternate_order(rates, cycle_index)
        if on_cycle_start:
            on_cycle_start(cycle_index, ordered)
        outcomes = run_cycle(path, ordered, cfg, on_rate_result=on_rate_result)
        cycles_run += 1
        for outcome in outcomes:
            scores[outcome.rate].append(outcome.score)
            if outcome.score >= threshold:
                hits[outcome.rate] += 1
            if outcome.score > best_score[outcome.rate]:
                best_score[outcome.rate] = outcome.score
                if outcome.breakdown is not None:
                    best_sample[outcome.rate] = outcome.breakdown.sample_text

    results = []
    denom = max(cycles_run, 1)
    for rate in rates:
        rate_scores = scores[rate]
        avg = sum(rate_scores) / len(rate_scores) if rate_scores else 0.0
        results.append(
            AggregateResult(
                rate=rate,
                hit_rate=hits[rate] / denom,
                avg_score=avg,
                best_score=best_score[rate],
                best_sample=best_sample[rate],
            )
        )

    results.sort(key=lambda r: (-r.hit_rate, -r.avg_score))
    return results, cycles_run
