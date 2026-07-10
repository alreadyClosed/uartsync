import time
import termios
from dataclasses import dataclass, field

import serial
from serial import SerialException


@dataclass
class CaptureConfig:
    probe_timeout_ms: int = 200
    capture_timeout_ms: int = 1500
    min_bytes: int = 50
    settle_ms: int = 15
    retries: int = 3
    retry_delay_ms: int = 150


@dataclass
class CaptureResult:
    rate: int
    raw: bytes = b""
    framing_errors: int = 0
    silent: bool = True
    error: str = ""
    elapsed_s: float = 0.0


def _enable_framing_detection(ser):
    fd = ser.fileno()
    attrs = termios.tcgetattr(fd)
    iflag = attrs[0]
    iflag |= termios.INPCK | termios.PARMRK
    iflag &= ~termios.IGNPAR
    attrs[0] = iflag
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def _strip_parmrk(raw):
    errors = 0
    cleaned = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        byte = raw[i]
        if byte == 0xFF:
            if i + 1 < n and raw[i + 1] == 0xFF:
                cleaned.append(0xFF)
                i += 2
                continue
            if i + 2 < n and raw[i + 1] == 0x00:
                errors += 1
                cleaned.append(raw[i + 2])
                i += 3
                continue
            cleaned.append(byte)
            i += 1
            continue
        cleaned.append(byte)
        i += 1
    return errors, bytes(cleaned)


def open_with_retries(path, baud, retries, retry_delay_ms):
    last_err = None
    for attempt in range(retries + 1):
        try:
            ser = serial.Serial()
            ser.port = path
            ser.baudrate = baud
            ser.bytesize = serial.EIGHTBITS
            ser.parity = serial.PARITY_NONE
            ser.stopbits = serial.STOPBITS_ONE
            ser.timeout = 0.2
            ser.open()
            return ser
        except SerialException as exc:
            last_err = exc
            time.sleep(retry_delay_ms / 1000.0)
    raise last_err


def capture_rate(path, baud, cfg: CaptureConfig):
    start = time.monotonic()
    try:
        ser = open_with_retries(path, baud, cfg.retries, cfg.retry_delay_ms)
    except SerialException as exc:
        return CaptureResult(rate=baud, error=str(exc), elapsed_s=time.monotonic() - start)

    try:
        ser.reset_input_buffer()
        time.sleep(cfg.settle_ms / 1000.0)
        try:
            _enable_framing_detection(ser)
        except (termios.error, OSError):
            pass

        ser.timeout = cfg.probe_timeout_ms / 1000.0
        first_chunk = ser.read(4096)
        if not first_chunk:
            return CaptureResult(rate=baud, silent=True, elapsed_s=time.monotonic() - start)

        raw = bytearray(first_chunk)
        deadline = start + (cfg.capture_timeout_ms / 1000.0)
        ser.timeout = 0.1
        while len(raw) < cfg.min_bytes and time.monotonic() < deadline:
            chunk = ser.read(4096)
            if chunk:
                raw.extend(chunk)

        errors, cleaned = _strip_parmrk(bytes(raw))
        return CaptureResult(
            rate=baud,
            raw=cleaned,
            framing_errors=errors,
            silent=False,
            elapsed_s=time.monotonic() - start,
        )
    finally:
        ser.close()
