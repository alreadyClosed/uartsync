import os
import time

from .constants import TTY_PATTERNS


class DeviceWaitAborted(Exception):
    pass


def list_tty_nodes():
    try:
        entries = os.listdir("/dev")
    except OSError:
        return set()
    return {e for e in entries if e.startswith(TTY_PATTERNS)}


def wait_for_new_device(poll_interval=0.1, settle_time=0.2, timeout=None, on_wait=None):
    baseline = list_tty_nodes()
    start = time.monotonic()
    while True:
        if timeout is not None and (time.monotonic() - start) > timeout:
            raise DeviceWaitAborted("timed out waiting for a new UART device")
        current = list_tty_nodes()
        new = sorted(current - baseline)
        if new:
            candidate = new[0]
            time.sleep(settle_time)
            if candidate in list_tty_nodes():
                return f"/dev/{candidate}"
            baseline = list_tty_nodes()
        if on_wait:
            on_wait()
        time.sleep(poll_interval)


def wait_for_specific_device(path, poll_interval=0.1, timeout=None, on_wait=None):
    start = time.monotonic()
    while not os.path.exists(path):
        if timeout is not None and (time.monotonic() - start) > timeout:
            raise DeviceWaitAborted(f"timed out waiting for {path} to appear")
        if on_wait:
            on_wait()
        time.sleep(poll_interval)
    return path


def list_available_ports():
    import serial.tools.list_ports

    return list(serial.tools.list_ports.comports())
