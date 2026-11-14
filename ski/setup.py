#!/usr/bin/env python3
"""Setup: install the hotel search tools into this app's own folder.

Creates .venv next to this file and installs two open source libraries:
  stays     Google Hotels search (needs Python 3.10 or newer)
  pyairbnb  Airbnb search
Nothing is installed outside this folder. Safe to run again: when the tools
are already there it changes nothing.

When the computer has no Python new enough (a Mac's built-in one is 3.9), it
downloads `uv` (an open source Python installer, https://docs.astral.sh/uv/)
into .tools/ in this folder and lets it fetch a private Python there.

Runs as the app's "Setup" routine. The last line printed is JSON for the
routine card; a non-zero exit with a one-line reason shows as failed.

Written to start on any Python 3 (macOS ships 3.9), so keep the syntax plain.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
TOOLS = HERE / ".tools"
PACKAGES = ["stays", "pyairbnb"]
MIN = (3, 10)
UV_INSTALLER = "https://astral.sh/uv/install.sh"
UV_PYTHON = "3.12"


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


def uv_env():
    """Keep everything uv downloads inside this app's folder."""
    env = dict(os.environ)
    env["UV_INSTALL_DIR"] = str(TOOLS / "bin")
    env["UV_NO_MODIFY_PATH"] = "1"
    env["UV_PYTHON_INSTALL_DIR"] = str(TOOLS / "python")
    env["UV_CACHE_DIR"] = str(TOOLS / "cache")
    return env


def find_uv():
    for exe in (TOOLS / "bin" / "uv", shutil.which("uv")):
        if exe and os.path.exists(str(exe)):
            return str(exe)
    return None


def get_uv():
    """uv from this folder or the machine; otherwise download it into .tools/."""
    uv = find_uv()
    if uv:
        return uv
    if os.name == "nt":
        fail("Hotel search needs Python 3.10 or newer. Install Python from python.org, then press Run now.")
    try:
        # The site refuses Python's default client name.
        req = urllib.request.Request(UV_INSTALLER, headers={"User-Agent": "curl/8.0"})
        script = urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        fail("Could not download the Python installer (is the internet on?): %s" % e)
    TOOLS.mkdir(exist_ok=True)
    done = subprocess.run(["sh", "-s"], input=script, capture_output=True, env=uv_env())
    uv = find_uv()
    if done.returncode != 0 or not uv:
        tail = [ln for ln in done.stderr.decode("utf-8", "replace").splitlines() if ln.strip()]
        fail("Could not install the Python installer: " + (tail[-1] if tail else "unknown error")[:200])
    return uv


def make_venv_with_uv():
    uv = get_uv()
    made = subprocess.run([uv, "venv", "--quiet", "--python", UV_PYTHON, str(VENV)],
                          capture_output=True, text=True, env=uv_env())
    if made.returncode != 0:
        tail = [ln for ln in (made.stderr or made.stdout).splitlines() if ln.strip()]
        fail("Could not set up a newer Python: " + (tail[-1] if tail else "uv failed")[:200])
    return uv


def tools_python_works():
    """True when the new environment has a Python that can run pip."""
    py = venv_python()
    if not py.exists():
        return False
    check = subprocess.run([str(py), "-m", "pip", "--version"], capture_output=True, text=True)
    return check.returncode == 0


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

    python = None if os.environ.get("SKI_SETUP_NO_SYSTEM_PYTHON") else find_python()

    # A half-built or too-old .venv is replaced rather than repaired.
    if VENV.exists() and (version_of(venv_python()) or (0, 0)) < MIN:
        shutil.rmtree(str(VENV), ignore_errors=True)
    uv = None
    if not venv_python().exists():
        if python:
            made = subprocess.run([python, "-m", "venv", str(VENV)], capture_output=True, text=True)
            if made.returncode != 0 or not tools_python_works():
                # Debian and Ubuntu ship Python without the venv add-on, and a
                # failed attempt leaves a half-built folder. Start clean and
                # fetch a private Python instead of asking for a system install.
                shutil.rmtree(str(VENV), ignore_errors=True)
                uv = make_venv_with_uv()
        else:
            # No Python new enough on this computer: fetch a private one.
            uv = make_venv_with_uv()

    if uv:  # a uv-made environment has no pip of its own
        pip = subprocess.run(
            [uv, "pip", "install", "--quiet", "--python", str(venv_python())] + PACKAGES,
            capture_output=True, text=True, env=uv_env())
    else:
        pip = subprocess.run(
            [str(venv_python()), "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + PACKAGES,
            capture_output=True, text=True)
    if pip.returncode != 0:
        tail = [ln for ln in (pip.stderr or pip.stdout).splitlines() if ln.strip()]
        fail("Could not download the hotel search tools (is the internet on?): "
             + (tail[-1] if tail else "pip failed")[:200])
    if not tools_ready():
        fail("The hotel search tools installed but will not load. Delete the .venv folder and run Setup again.")

    shutil.rmtree(str(TOOLS / "cache"), ignore_errors=True)  # download leftovers
    mark_search_live()
    print(json.dumps({"summary": "Installed the hotel search tools (Google Hotels and Airbnb)."}))


if __name__ == "__main__":
    main()
