import math
import re
from dataclasses import dataclass

PRINTABLE = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}

COMMON_BIGRAMS = {
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd",
    "ti", "es", "or", "te", "of", "ed", "is", "it", "al", "ar",
    "st", "to", "nt", "ng", "se", "ha", "as", "ou", "io", "le",
    "ve", "co", "me", "de", "hi", "ri", "ro", "ic", "ne", "ea",
    "ra", "ce", "li", "ch", "ll", "be", "ma", "si", "om", "ur",
}

COMMON_WORDS = frozenset({
    "the", "and", "for", "are", "not", "you", "with", "from", "this",
    "that", "have", "was", "were", "will", "can", "all", "your", "has",
    "more", "which", "their", "one", "about", "out", "who", "get", "when",
    "make", "than", "into", "time", "some", "could", "them", "see", "other",
    "then", "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first", "well",
    "way", "even", "new", "want", "any", "these", "give", "day", "most",
    "boot", "boots", "booting", "kernel", "linux", "login", "password",
    "init", "system", "error", "errors", "warning", "warnings", "memory",
    "welcome", "version", "ready", "start", "started", "starting", "network",
    "config", "configuration", "device", "devices", "driver", "drivers",
    "module", "modules", "mount", "mounted", "mounting", "root", "shell",
    "prompt", "console", "enable", "enabled", "disable", "disabled", "cpu",
    "flash", "partition", "partitions", "filesystem", "checking", "check",
    "done", "failed", "success", "successful", "load", "loading", "loaded",
    "reset", "power", "user", "uart", "serial", "port", "address", "size",
    "bytes", "block", "blocks", "image", "images", "firmware", "hardware",
    "software", "bootloader", "uboot", "kernel", "initrd", "revision",
    "processor", "clock", "interrupt", "controller", "interface", "ethernet",
    "wireless", "connected", "connection", "server", "client", "host",
})


@dataclass
class ScoreBreakdown:
    total: float
    best_line_quality: float
    good_line_fraction: float
    line_count: int
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
        return 1.0
    if entropy < low:
        return max(0.0, entropy / low)
    spread = 8.0 - high
    if spread <= 0:
        return 0.0
    return max(0.0, 1.0 - (entropy - high) / spread)


def _extract_words(buf):
    text = buf.decode("ascii", errors="ignore").lower()
    return re.findall(r"[a-z]{3,}", text)


def _bigram_ratio(words):
    pairs = 0
    hits = 0
    for word in words:
        for i in range(len(word) - 1):
            pairs += 1
            if word[i:i + 2] in COMMON_BIGRAMS:
                hits += 1
    if pairs == 0:
        return 0.0
    return hits / pairs


def _word_hit_ratio(words):
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in COMMON_WORDS)
    return hits / len(words)


def _pattern_bonus(buf):
    if re.search(rb"[-=_*#]{3,}", buf):
        return 5.0
    return 0.0


def _line_quality(line: bytes):
    if not line:
        return 0.0
    printable_ratio = _printable_ratio(line)
    words = _extract_words(line)
    word_hit_ratio = _word_hit_ratio(words)
    bigram_ratio = _bigram_ratio(words)
    entropy = _shannon_entropy(line)
    entropy_score = _entropy_score(entropy)
    pattern_bonus = _pattern_bonus(line)

    quality = (
        (printable_ratio * 15.0)
        + (word_hit_ratio * 50.0)
        + (bigram_ratio * 20.0)
        + (entropy_score * 10.0)
        + pattern_bonus
    )
    return max(0.0, min(100.0, quality))


def _split_lines(raw: bytes):
    parts = re.split(rb"[\r\n]+", raw)
    return [p for p in parts if len(p) >= 2]


def score_capture(raw: bytes, framing_errors: int) -> ScoreBreakdown:
    sample_text = raw[:120].decode("ascii", errors="replace")

    if framing_errors > 0:
        return ScoreBreakdown(
            total=0.0,
            best_line_quality=0.0,
            good_line_fraction=0.0,
            line_count=0,
            framing_errors=framing_errors,
            disqualified=True,
            sample_text=sample_text,
        )

    if not raw:
        return ScoreBreakdown(
            total=0.0,
            best_line_quality=0.0,
            good_line_fraction=0.0,
            line_count=0,
            framing_errors=0,
            disqualified=False,
            sample_text="",
        )

    lines = _split_lines(raw)
    if not lines:
        lines = [raw]

    qualities = [(_line_quality(line), line) for line in lines]
    qualities.sort(key=lambda pair: pair[0], reverse=True)

    best_quality, best_line = qualities[0]
    top_slice = qualities[:3]
    avg_top = sum(q for q, _ in top_slice) / len(top_slice)
    good_fraction = sum(1 for q, _ in qualities if q >= 50.0) / len(qualities)

    total = (best_quality * 0.55) + (avg_top * 0.25) + (good_fraction * 100.0 * 0.20)
    total = max(0.0, min(100.0, total))

    best_sample = best_line[:120].decode("ascii", errors="replace")

    return ScoreBreakdown(
        total=total,
        best_line_quality=best_quality,
        good_line_fraction=good_fraction,
        line_count=len(lines),
        framing_errors=0,
        disqualified=False,
        sample_text=best_sample,
    )