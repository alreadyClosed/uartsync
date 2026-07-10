import argparse
import sys
import time

from .constants import DEFAULT_RATES, SCORE_THRESHOLD
from .devicewatch import (
    wait_for_new_device,
    wait_for_specific_device,
    list_available_ports,
    DeviceWaitAborted,
)
from .capture import CaptureConfig
from .scan import run_scan
from .launcher import launch_interactive_session


def parse_rates(value):
    if value.lower() == "all":
        return list(DEFAULT_RATES)
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        result.append(int(part))
    return result


def build_parser():
    parser = argparse.ArgumentParser(
        prog="uartsync",
        description="Automatic UART baud rate detection tool",
    )
    parser.add_argument("device", nargs="?", default=None,
                         help="Serial device path, e.g. /dev/ttyUSB0. If omitted, waits for a new tty node to appear")
    parser.add_argument("--rates", default="all",
                         help="Comma separated list of baud rates to test, or 'all'")
    parser.add_argument("--repeat", type=int, default=1,
                         help="Number of scan cycles to run")
    parser.add_argument("--timeout", type=float, default=60,
                         help="Hard ceiling in seconds, counted from device detection")
    parser.add_argument("--min-bytes", type=int, default=50,
                         help="Bytes to collect per rate before scoring")
    parser.add_argument("--probe-timeout", type=int, default=200,
                         help="Milliseconds to wait for any byte activity before marking a rate silent")
    parser.add_argument("--capture-timeout", type=int, default=1500,
                         help="Milliseconds ceiling to fill min-bytes once activity is detected")
    parser.add_argument("--retries", type=int, default=3,
                         help="Retries on device open failure")
    parser.add_argument("--retry-delay", type=int, default=150,
                         help="Milliseconds between open retries")
    parser.add_argument("--settle-ms", type=int, default=15,
                         help="Delay after setting baud rate before reading")
    parser.add_argument("--threshold", type=float, default=SCORE_THRESHOLD,
                         help="Score threshold for a rate to count as a hit")
    parser.add_argument("--verbose", action="store_true",
                         help="Show per rate score breakdown")
    parser.add_argument("--apply", action="store_true",
                         help="Launch an interactive session at the winning rate")
    parser.add_argument("--list", action="store_true",
                         help="List currently available serial devices and exit")
    return parser


def cmd_list():
    ports = list_available_ports()
    if not ports:
        print("No serial devices found.")
        return
    for port in ports:
        print(f"{port.device}\t{port.description}\t{port.hwid}")


def resolve_device(args):
    remaining = None
    if args.timeout:
        remaining = args.timeout

    if args.device:
        print(f"Waiting for {args.device} ...")
        try:
            path = wait_for_specific_device(args.device, timeout=remaining)
        except DeviceWaitAborted as exc:
            print(f"Error: {exc}")
            sys.exit(1)
    else:
        print("Waiting for UART device...")
        try:
            path = wait_for_new_device(timeout=remaining)
        except DeviceWaitAborted as exc:
            print(f"Error: {exc}")
            sys.exit(1)

    print(f"Detected {path}")
    return path


def print_cycle_header(index, ordered):
    direction = "common -> uncommon" if index % 2 == 0 else "uncommon -> common"
    print(f"\nCycle {index + 1} ({direction})")


def print_rate_result(outcome, verbose):
    if outcome.silent:
        status = f"silent"
        if outcome.error:
            status = f"error: {outcome.error}"
        print(f"  {outcome.rate:<8} ..... {status}")
        return

    print(f"  {outcome.rate:<8} ..... data received, score {outcome.score:.0f}")
    if verbose and outcome.breakdown is not None:
        b = outcome.breakdown
        if b.disqualified:
            print(f"           framing errors={b.framing_errors}")
        else:
            print(
                f"           printable={b.printable_ratio:.2f} "
                f"entropy={b.entropy:.2f} line_score={b.line_score:.0f} "
                f"pattern_score={b.pattern_score:.0f}"
            )


def print_results_table(results):
    print("\n=== Results ===")
    header = f"{'Rank':<5}{'Rate':<10}{'Hit rate':<12}{'Avg score':<12}Sample"
    print(header)
    for i, r in enumerate(results[:3], start=1):
        hit_pct = f"{r.hit_rate * 100:.0f}%"
        sample = r.best_sample.replace("\r", "\\r").replace("\n", "\\n")
        if len(sample) > 40:
            sample = sample[:40] + "..."
        print(f"{i:<5}{r.rate:<10}{hit_pct:<12}{r.avg_score:<12.1f}{sample}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        cmd_list()
        return

    try:
        rates = parse_rates(args.rates)
    except ValueError:
        print("Error: could not parse --rates, expected comma separated integers or 'all'")
        sys.exit(1)

    if not rates:
        print("Error: no rates to test")
        sys.exit(1)

    path = resolve_device(args)

    cfg = CaptureConfig(
        probe_timeout_ms=args.probe_timeout,
        capture_timeout_ms=args.capture_timeout,
        min_bytes=args.min_bytes,
        settle_ms=args.settle_ms,
        retries=args.retries,
        retry_delay_ms=args.retry_delay,
    )

    deadline = time.monotonic() + args.timeout if args.timeout else None

    def on_cycle_start(index, ordered):
        print_cycle_header(index, ordered)

    def on_rate_result(outcome):
        print_rate_result(outcome, args.verbose)

    results, cycles_run = run_scan(
        path,
        rates,
        cfg,
        repeat=args.repeat,
        threshold=args.threshold,
        deadline=deadline,
        on_cycle_start=on_cycle_start,
        on_rate_result=on_rate_result,
    )

    print(f"\nCompleted {cycles_run} cycle(s).")
    print_results_table(results)

    if not results or results[0].hit_rate == 0:
        print("\nNo confident match found. The device may need a power cycle, or try different rates.")
        return

    best = results[0]
    print(f"\nBest match: {best.rate} baud ({best.hit_rate * 100:.0f}% confidence)")

    if args.apply:
        tool = launch_interactive_session(path, best.rate)
        if tool is None:
            print("Could not find screen or picocom on this system to launch a session.")
    else:
        print("Run with --apply to launch an interactive session automatically.")


if __name__ == "__main__":
    main()
