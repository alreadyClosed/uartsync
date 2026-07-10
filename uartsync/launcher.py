import shutil
import subprocess


def launch_interactive_session(path, baud):
    if shutil.which("picocom"):
        subprocess.call(["picocom", "-b", str(baud), path])
        return "picocom"
    if shutil.which("screen"):
        subprocess.call(["screen", path, str(baud)])
        return "screen"
    return None
