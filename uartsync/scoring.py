import math
import re
from dataclasses import dataclass, field

PRINTABLE = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}


@dataclass
class ScoreBreakdown:
    total: float
    printable_ratio: float
    entropy: float
    entropy_score: float
    line_score: float
    pattern_score: float
    framing_errors: int
    disqualified: bool
    sample_text: str


def _printable_ratio(buf):
    if not buf:
        return 0.0
    hits = sum(1 for b in buf if b in PRINTABLE)
    return hits / len(buf)


def _shannon_entropy(buf):
    if not buf:
        return 0.0
    counts = [0] * 256
    for b in buf:
        counts[b] += 1
    n = len(buf)
    entropy = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / n
        entropy -= p * math.log2(p)
    return entropy


def _entropy_score(entropy):
    low, high = 3.0, 5.5
    if low <= entropy <= high:
        return 25.0
    if entropy < low:
        return max(0.0, 25.0 * (entropy / low))
    spread = 8.0 - high
    if spread <= 0:
        return 0.0
    return max(0.0, 25.0 * (1.0 - (entropy - high) / spread))


def _line_score(buf):
    if not buf:
        return 0.0
    newlines = buf.count(b"\n")
    if newlines == 0:
        return 0.0
    avg_len = len(buf) / newlines
    if 5 <= avg_len <= 200:
        return 25.0
    if avg_len < 5:
        return max(0.0, 25.0 * (avg_len / 5))
    return max(0.0, 25.0 * (200 / avg_len))


def _pattern_score(buf):
    if re.search(rb"[-=_*#]{3,}", buf):
        return 10.0
    return 0.0


def score_capture(raw: bytes, framing_errors: int) -> ScoreBreakdown:
    sample_text = raw[:120].decode("ascii", errors="replace")

    if framing_errors > 0:
        return ScoreBreakdown(
            total=0.0,
            printable_ratio=0.0,
            entropy=0.0,
            entropy_score=0.0,
            line_score=0.0,
            pattern_score=0.0,
            framing_errors=framing_errors,
            disqualified=True,
            sample_text=sample_text,
        )

    if not raw:
        return ScoreBreakdown(
            total=0.0,
            printable_ratio=0.0,
            entropy=0.0,
            entropy_score=0.0,
            line_score=0.0,
            pattern_score=0.0,
            framing_errors=0,
            disqualified=False,
            sample_text="",
        )

    printable_ratio = _printable_ratio(raw)
    entropy = _shannon_entropy(raw)
    entropy_score = _entropy_score(entropy)
    line_score = _line_score(raw)
    pattern_score = _pattern_score(raw)

    total = (printable_ratio * 40.0) + line_score + entropy_score + pattern_score
    total = max(0.0, min(100.0, total))

    return ScoreBreakdown(
        total=total,
        printable_ratio=printable_ratio,
        entropy=entropy,
        entropy_score=entropy_score,
        line_score=line_score,
        pattern_score=pattern_score,
        framing_errors=0,
        disqualified=False,
        sample_text=sample_text,
    )
