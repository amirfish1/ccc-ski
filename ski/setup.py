#!/usr/bin/env python3
"""Setup: install the hotel search tools into this app's own folder.

Creates .venv next to this file and installs two open source libraries:
  stays     Google Hotels search (needs Python 3.10 or newer)
  pyairbnb  Airbnb search
Nothing is installed outside this folder. Safe to run again: when the tools
are already there it changes nothing.

Runs as the app's "Setup" routine. The last line printed is JSON for the
routine card; a non-zero exit with a one-line reason shows as failed.

Written to start on any Python 3 (macOS ships 3.9), so keep the syntax plain.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
PACKAGES = ["stays", "pyairbnb"]
MIN = (3, 10)


def fail(reason):
    print(reason, file=sys.stderr)
    sys.exit(1)


def venv_python():
    win = VENV / "Scripts" / "python.exe"
    return win if win.exists() else VENV / "bin" / "python"


def version_of(exe):
    try:
        out = subprocess.run(
            [str(exe), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True, text=True, timeout=20)
        major, minor = out.stdout.split()
        return int(major), int(minor)
    except Exception:
        return None


def find_python():
    """A Python new enough for the tools: this one, or a newer one on the machine."""
    if sys.version_info[:2] >= MIN:
        return sys.executable
    names = ["python3.%d" % m for m in range(14, MIN[1] - 1, -1)]
    dirs = ["/opt/homebrew/bin", "/usr/local/bin",
            "/Library/Frameworks/Python.framework/Versions/Current/bin",
            str(Path.home() / ".local" / "bin")]
    for name in names:
        found = shutil.which(name)
        candidates = [found] if found else []
        candidates += [os.path.join(d, name) for d in dirs]
        for exe in candidates:
            if exe and os.path.exists(exe) and (version_of(exe) or (0, 0)) >= MIN:
                return exe
    return None


def tools_ready():
    py = venv_python()
    if not py.exists():
        return False
    check = subprocess.run([str(py), "-c", "import stays, pyairbnb"],
                           capture_output=True, text=True)
    return check.returncode == 0


def mark_search_live():
    """Flip the "Hotel search" tile on the page from "Not set up" to "Live"."""
    path = HERE / "app.json"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for part in meta.get("topic", {}).get("parts", []):
            if part.get("id") == "search" and part.get("status") != "live":
                part["status"] = "live"
                part["how"] = "Ask the agent to search a weekend. It checks Google Hotels and Airbnb."
                changed = True
        if changed:
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
    except Exception:
        pass  # The tile is cosmetic; the tools still work.


def main():
    if tools_ready():
        mark_search_live()
        print(json.dumps({"summary": "Hotel search tools are already installed."}))
        return

    python = find_python()
    if not python:
        fail("Hotel search needs Python 3.10 or newer and this computer has %d.%d. "
             "Install Python from python.org, then press Run now."
             % (sys.version_info[0], sys.version_info[1]))

    # A half-built or too-old .venv is replaced rather than repaired.
    if VENV.exists() and (version_of(venv_python()) or (0, 0)) < MIN:
        shutil.rmtree(str(VENV), ignore_errors=True)
    if not venv_python().exists():
        made = subprocess.run([python, "-m", "venv", str(VENV)], capture_output=True, text=True)
        if made.returncode != 0:
            tail = (made.stderr or made.stdout).strip().splitlines()
            fail("Could not create the tools folder: " + (tail[-1] if tail else "venv failed"))

    pip = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + PACKAGES,
        capture_output=True, text=True)
    if pip.returncode != 0:
        tail = [ln for ln in (pip.stderr or pip.stdout).splitlines() if ln.strip()]
        fail("Could not download the hotel search tools (is the internet on?): "
             + (tail[-1] if tail else "pip failed")[:200])
    if not tools_ready():
        fail("The hotel search tools installed but will not load. Delete the .venv folder and run Setup again.")

    mark_search_live()
    print(json.dumps({"summary": "Installed the hotel search tools (Google Hotels and Airbnb)."}))


if __name__ == "__main__":
    main()
