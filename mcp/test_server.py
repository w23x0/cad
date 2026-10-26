#!/usr/bin/env python3
"""End-to-end test for mcp/server.py: speak MCP JSON-RPC over stdio.

Launches the real server as a subprocess and drives the full tool contract:
initialize handshake -> tools/list -> engines -> run_script (both kernels,
persistent session) -> measure -> export -> snapshot -> reset (then verify the
session is really empty). Exit code 0 = all checks passed.

Stdlib only. The wire format is newline-delimited JSON-RPC 2.0 on the
server's stdin/stdout; tool results come back as JSON inside
result.content[0].text.

Run with an interpreter that has the `mcp` package (the same one you would
use to start the server):

    CAD_B123D_PYTHON=/path/to/b123d-python \
    CAD_SMLIBPY_PYTHON=/path/to/smlibpy-python \
        /path/to/b123d-python mcp/test_server.py
"""
from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER = Path(__file__).resolve().with_name("server.py")

CALL_TIMEOUT_S = 60.0     # per JSON-RPC request
SHUTDOWN_TIMEOUT_S = 20.0


def _smlibpy_python() -> str:
    candidates = [
        os.environ.get("CAD_SMLIBPY_PYTHON"),
        str(REPO_ROOT.parent / "smlibpy" / "venv" / "bin" / "python"),
        str(Path.home() / "CAD" / "smlibpy" / "venv" / "bin" / "python"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return ""

class Fail(Exception):
    pass


_checks = {"passed": 0}


def check(cond: bool, label: str) -> None:
    if not cond:
        raise Fail(label)
    _checks["passed"] += 1
    print(f"  ok: {label}")


class McpClient:
    """Tiny MCP stdio client: newline-delimited JSON-RPC, with timeouts."""

    def __init__(self, env: dict[str, str]):
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER)],
            cwd=str(REPO_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self._buf = b""
        self._sel = selectors.DefaultSelector()
        self._sel.register(self.proc.stdout, selectors.EVENT_READ)
        self._stderr_tail: list[str] = []
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()
        self._id = 0

    def _drain_stderr(self) -> None:
        # Keep the pipe drained so the server never blocks on a full stderr.
        for raw in self.proc.stderr:
            self._stderr_tail.append(raw.rstrip())
            del self._stderr_tail[:-50]

    def _read_line(self, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        while b"\n" not in self._buf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Fail(f"timed out after {timeout:.0f}s waiting for the server "
                           f"(last bytes: {self._buf[-200:]!r})")
            events = self._sel.select(remaining)
            if not events:
                continue
            if any(key.fileobj is self.proc.stdout for key, _ in events):
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    self._dump_stderr("server closed stdout early")
                    raise Fail(f"server exited (code {self.proc.poll()}) before answering")
                self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return line

    def request(self, method: str, params: dict | None = None,
                *, notify: bool = False, timeout: float = CALL_TIMEOUT_S) -> dict:
        self._id += 1
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            msg["id"] = self._id
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        self.proc.stdin.flush()
        if notify:
            return {}
        resp = json.loads(self._read_line(timeout))
        if resp.get("id") != self._id:
            raise Fail(f"response id mismatch: expected {self._id}, got {resp.get('id')}")
        if "error" in resp:
            raise Fail(f"{method} returned JSON-RPC error: {resp['error']}")
        return resp["result"]

    def call_tool(self, name: str, arguments: dict | None = None,
                  timeout: float = CALL_TIMEOUT_S) -> dict:
        """tools/call and return the tool's own return value as parsed JSON."""
        result = self.request("tools/call",
                              {"name": name, "arguments": arguments or {}},
                              timeout=timeout)
        if result.get("isError"):
            raise Fail(f"{name} reported isError: {result.get('content')}")
        blocks = result.get("content") or []
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        if not texts:
            raise Fail(f"{name} returned no text content: {result}")
        return json.loads(texts[0])

    def shutdown(self) -> str:
        """Close stdin (EOF), escalate to terminate/kill; return how it ended."""
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            code = self.proc.wait(timeout=SHUTDOWN_TIMEOUT_S)
            return f"exited with code {code} after stdin EOF"
        except subprocess.TimeoutExpired:
            pass
        self.proc.terminate()
        try:
            code = self.proc.wait(timeout=5)
            return f"terminated (exit code {code})"
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
            return "killed"

    def _dump_stderr(self, why: str) -> None:
        if self._stderr_tail:
            print(f"--- server stderr ({why}) ---", file=sys.stderr)
            print("\n".join(self._stderr_tail), file=sys.stderr)


def approx(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def main() -> int:
    out_dir = Path(tempfile.mkdtemp(prefix="cad_mcp_e2e_"))
    b123d_python = os.environ.get("CAD_B123D_PYTHON") or sys.executable
    smlibpy_python = _smlibpy_python()
    # An explicitly set but broken interpreter variable must fail loudly:
    # otherwise the server's fallbacks would silently test a different kernel
    # than the one the caller asked for.
    for var in ("CAD_B123D_PYTHON", "CAD_SMLIBPY_PYTHON"):
        explicit = os.environ.get(var)
        if explicit and not Path(explicit).is_file():
            print(f"FAIL: {var} is set but is not a file: {explicit}")
            return 1
    if not smlibpy_python:
        print("FAIL: no smlibpy interpreter found; "
              "set CAD_SMLIBPY_PYTHON to the smlibpy venv python")
        return 1

    env = dict(os.environ,
               CAD_B123D_PYTHON=b123d_python,
               CAD_SMLIBPY_PYTHON=smlibpy_python,
               CAD_OUT=str(out_dir))
    client = McpClient(env)
    print(f"server pid {client.proc.pid}, CAD_OUT={out_dir}")
    shutdown_note = "not shut down"
    try:
        run_tests(client, out_dir, Path(b123d_python), Path(smlibpy_python))
    except Fail as exc:
        client._dump_stderr("failure")
        print(f"FAIL: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - report anything as test failure
        client._dump_stderr(f"unexpected {type(exc).__name__}")
        print(f"FAIL: unexpected {type(exc).__name__}: {exc}")
        return 1
    finally:
        shutdown_note = client.shutdown()
        print(f"server shutdown: {shutdown_note}")
        shutil.rmtree(out_dir, ignore_errors=True)
        if out_dir.exists():
            print(f"note: could not remove {out_dir}")

    print(f"ALL {_checks['passed']} CHECKS PASSED")
    return 0


def run_tests(client: McpClient, out_dir: Path,
              b123d_python: Path, smlibpy_python: Path) -> None:
    # -- initialize handshake ------------------------------------------------
    print("[1] initialize")
    init = client.request("initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "mcp-e2e-test", "version": "0"},
    })
    check(init.get("protocolVersion") == "2025-06-18", "protocol version negotiated")
    check(init.get("serverInfo", {}).get("name") == "cad", "serverInfo.name == 'cad'")
    check(isinstance(init.get("instructions"), str) and init["instructions"],
          "instructions present")
    client.request("notifications/initialized", notify=True)

    # -- tools/list ----------------------------------------------------------
    print("[2] tools/list")
    tools = {t["name"] for t in client.request("tools/list")["tools"]}
    expected = {"engines", "run_script", "measure", "export", "snapshot", "reset"}
    check(expected <= tools, f"all 6 tools listed (got {sorted(tools)})")

    # -- engines -------------------------------------------------------------
    print("[3] engines")
    engines = client.call_tool("engines")["engines"]
    check(engines["build123d"]["path_exists"] is True, "build123d interpreter found")
    check(engines["smlibpy"]["path_exists"] is True, "smlibpy interpreter found")

    # -- run_script on both kernels ------------------------------------------
    print("[4] run_script (Box - Cylinder on both kernels)")
    box_code = ("from {mod} import *\n"
                "wall = 60\n"
                "result = Box(80, wall, 10) - Cylinder(4, 12)")
    persist_code = ("assert wall == 60\n"
                    "result = Box(80, wall, 10) - Cylinder(4, 12)")
    metrics: dict[str, dict] = {}
    for engine, mod in (("build123d", "build123d"), ("smlibpy", "smlibpy")):
        r = client.call_tool("run_script", {"engine": engine,
                                            "code": box_code.format(mod=mod)})
        check(r.get("ok") is True, f"{engine}: run_script ok")
        m = r.get("metrics") or {}
        check(m.get("volume_mm3") is not None and m.get("bbox_mm") is not None,
              f"{engine}: run_script returned metrics")
        # persistence: second script still sees `wall` and rebuilds the shape
        r2 = client.call_tool("run_script", {"engine": engine, "code": persist_code})
        check(r2.get("ok") is True and r2.get("metrics", {}).get("volume_mm3"),
              f"{engine}: session persisted variables across run_script calls")
        metrics[engine] = r["metrics"]

    running = client.call_tool("engines")["engines"]
    check(running["build123d"]["running"] is True and running["smlibpy"]["running"] is True,
          "both persistent workers are alive after run_script")

    # -- measure -------------------------------------------------------------
    print("[5] measure")
    analytic = 80 * 60 * 10 - 3.141592653589793 * 4 ** 2 * 10  # plate minus through-hole
    for engine, m in metrics.items():
        vol = m["volume_mm3"]
        check(approx(vol, analytic, analytic * 1e-3),
              f"{engine}: volume {vol:.2f} within 0.1% of analytic {analytic:.2f}")
        check(all(approx(got, want, 1e-3) for got, want in zip(m["bbox_mm"], [80.0, 60.0, 10.0])),
              f"{engine}: bbox {m['bbox_mm']} == [80, 60, 10]")
        check(m.get("solids") == 1 and m.get("valid") is True,
              f"{engine}: one valid solid")
        check(m.get("faces", 0) >= 5, f"{engine}: face count sane ({m.get('faces')})")
    vols = [metrics[e]["volume_mm3"] for e in ("build123d", "smlibpy")]
    check(approx(vols[0], vols[1], max(vols) * 1e-3),
          f"kernels agree on volume: {vols[0]:.2f} vs {vols[1]:.2f}")
    live = client.call_tool("measure", {"engine": "build123d"})
    check(live.get("ok") is True and live["metrics"]["volume_mm3"] > 0,
          "measure returns the same session shape on a fresh call")

    # -- export --------------------------------------------------------------
    print("[6] export")
    for engine in ("build123d", "smlibpy"):
        target = out_dir / f"{engine}_e2e.step"
        r = client.call_tool("export", {"engine": engine, "path": str(target),
                                        "format": "step"})
        check(r.get("ok") is True, f"{engine}: export ok ({r.get('path')})")
        check(target.is_file() and target.stat().st_size > 100,
              f"{engine}: STEP file written ({target.name}, "
              f"{target.stat().st_size if target.exists() else 0} bytes)")

    # -- snapshot ------------------------------------------------------------
    print("[7] snapshot")
    for engine, view in (("build123d", "iso"), ("smlibpy", "iso"), ("build123d", "sheet")):
        target = out_dir / f"{engine}_{view}.png"
        r = client.call_tool("snapshot", {"engine": engine, "path": str(target),
                                          "view": view})
        check(r.get("ok") is True, f"{engine}: snapshot({view}) ok")
        check(target.is_file() and target.stat().st_size > 1000,
              f"{engine}: PNG written ({target.name}, "
              f"{target.stat().st_size if target.exists() else 0} bytes)")

    # -- reset ---------------------------------------------------------------
    print("[8] reset clears the session")
    for engine in ("build123d", "smlibpy"):
        r = client.call_tool("reset", {"engine": engine})
        check(r.get("ok") is True, f"{engine}: reset ok")
        after = client.call_tool("measure", {"engine": engine})
        check(after.get("ok") is False and "no shape" in after.get("error", ""),
              f"{engine}: measure after reset reports an empty session")


if __name__ == "__main__":
    raise SystemExit(main())
