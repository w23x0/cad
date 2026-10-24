#!/usr/bin/env python3
"""Unified CAD MCP server: one tool contract over two independent kernels.

Engines:
    smlibpy   SMLib / NURBS  (separate venv, Python 3.14)
    build123d OCCT / B-rep   (this venv,  Python 3.13)

Tools: run_script, measure, export, snapshot, reset, engines.
Each engine keeps a persistent worker process, so variables survive between
calls. The same script contract works on both: put the final shape in
`result`.

Run:  <interpreter-with-build123d> mcp/server.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from mcp.server.mcpserver import MCPServer

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = Path(os.environ.get("CAD_OUT") or REPO_ROOT / "out")
WORKER = Path(__file__).resolve().with_name("worker.py")


def _default_smlibpy() -> Path:
    candidates = [
        os.environ.get("CAD_SMLIBPY_PYTHON"),
        str(REPO_ROOT.parent / "smlibpy" / "venv" / "bin" / "python"),
        str(Path.home() / "CAD" / "smlibpy" / "venv" / "bin" / "python"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return Path("python3")


ENGINE_PYTHON = {
    "smlibpy": _default_smlibpy(),
    "build123d": Path(os.environ.get("CAD_B123D_PYTHON") or sys.executable),
}
ALIASES = {
    "smlibpy": "smlibpy",
    "sm": "smlibpy",
    "sml": "smlibpy",
    "build123d": "build123d",
    "b123d": "build123d",
    "b3d": "build123d",
    "occt": "build123d",
    "b-rep": "build123d",
}

INSTRUCTIONS = """\
Unified two-kernel CAD workspace. Use `smlibpy` (SMLib/NURBS) as the primary
kernel and `build123d` (OCCT) as an independent check; when a model matters,
build it in both and compare `measure` output (volume, bbox, solids, valid).

Workflow:
1. run_script(engine, code) — set `result` to the final shape. The session is
   persistent: variables and imports stay available between calls.
2. measure(engine) — volume / bbox / solids / faces / edges / validity.
3. snapshot(engine, view="iso") — PNG you can look at. build123d also supports
   view="sheet" (technical drawing with hidden lines); smlibpy supports
   iso/front/top/right/left/back/bottom.
4. export(engine, path, format) — STEP/STL/DXF/glTF/OBJ, best-effort per kernel.

Conventions: millimetres, degrees, Z up. Select geometry by properties, never
by index. Do not print huge outputs. Always verify numbers before exporting.
Relative paths resolve under $CAD_OUT/<engine>/ (default: <repo>/out).
"""

mcp = MCPServer(name="cad", instructions=INSTRUCTIONS)


class Worker:
    def __init__(self, engine: str):
        self.engine = engine
        python = ENGINE_PYTHON[engine]
        if not python.exists():
            raise RuntimeError(f"{engine} interpreter missing: {python}")
        env = dict(os.environ, PYTHONUNBUFFERED="1", CAD_ROOT=str(REPO_ROOT))
        self.proc = subprocess.Popen(
            [str(python), str(WORKER)],
            cwd=str(REPO_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )
        self.lock = threading.Lock()
        self.seq = 0

    def call(self, op: str, **kwargs) -> dict:
        with self.lock:
            self.seq += 1
            req = {"id": self.seq, "op": op, **kwargs}
            assert self.proc.stdin and self.proc.stdout
            self.proc.stdin.write(json.dumps(req) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.engine} worker exited unexpectedly")
            return json.loads(line)

    def close(self):
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
        except Exception:
            pass


_workers: dict[str, Worker] = {}
_registry_lock = threading.Lock()


def _worker(engine: str) -> Worker:
    key = ALIASES.get(engine.lower().strip())
    if key is None:
        raise ValueError(f"unknown engine {engine!r}; use one of {sorted(set(ALIASES))}")
    with _registry_lock:
        if key not in _workers or _workers[key].proc.poll() is not None:
            _workers[key] = Worker(key)
        return _workers[key]


def _resolve(engine: str, path: str, default_name: str) -> Path:
    key = ALIASES.get(engine.lower().strip(), engine)
    p = Path(path).expanduser() if path else OUT_ROOT / key / default_name
    if not p.is_absolute():
        p = OUT_ROOT / key / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@mcp.tool()
def engines() -> dict:
    """List the kernels, their interpreters, and whether the worker is alive."""
    return {
        "engines": {
            name: {
                "python": str(py),
                "path_exists": py.exists(),
                "running": name in _workers and _workers[name].proc.poll() is None,
            }
            for name, py in ENGINE_PYTHON.items()
        }
    }


@mcp.tool()
def run_script(engine: str, code: str) -> dict:
    """Run Python code in a persistent kernel session.

    `engine` is "smlibpy" or "build123d". The final shape must be assigned to
    `result`. Returns stdout and metrics (volume_mm3, bbox_mm, solids, faces,
    edges, valid). Variables persist until reset().
    """
    resp = _worker(engine).call("exec", code=code)
    if not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", "worker error")}
    return {"ok": True, "stdout": resp.get("stdout", ""), "metrics": resp.get("metrics")}


@mcp.tool()
def measure(engine: str) -> dict:
    """Measure the current shape of an engine session (volume, bbox, solids, edges)."""
    resp = _worker(engine).call("measure")
    if not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", "worker error")}
    if resp.get("metrics") is None:
        return {"ok": False, "error": "no shape in session; run_script first"}
    return {"ok": True, "metrics": resp["metrics"]}


@mcp.tool()
def export(engine: str, path: str = "", format: str = "") -> dict:
    """Export the current shape. Format defaults to the path suffix (step/stl/dxf/gltf/obj).

    Relative paths resolve under $CAD_OUT/<engine>/ (default: <repo>/out).
    """
    fmt = (format or Path(path or "model.step").suffix.lstrip(".") or "step").lower()
    default = f"model.{fmt}"
    target = _resolve(engine, path, default)
    resp = _worker(engine).call("export", path=str(target), format=fmt)
    if not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", "worker error")}
    return {"ok": True, **resp.get("file", {})}


@mcp.tool()
def snapshot(engine: str, path: str = "", view: str = "iso") -> dict:
    """Render the current shape to PNG.

    Views: iso / front / back / left / right / top / bottom; build123d also
    accepts "sheet" (technical drawing with hidden lines). Relative paths
    resolve under $CAD_OUT/<engine>/.
    """
    target = _resolve(engine, path, f"snapshot_{view}.png")
    resp = _worker(engine).call("snapshot", path=str(target), view=view)
    if not resp.get("ok"):
        return {"ok": False, "error": resp.get("error", "worker error")}
    return {"ok": True, **resp.get("file", {})}


@mcp.tool()
def reset(engine: str) -> dict:
    """Clear an engine session (drop all variables and the current shape)."""
    resp = _worker(engine).call("reset")
    return {"ok": bool(resp.get("ok")), "engine": engine}


def main() -> None:
    try:
        mcp.run("stdio")
    finally:
        for w in _workers.values():
            w.close()


if __name__ == "__main__":
    main()
