# mcp — one CAD tool contract, two kernels

```
agent ── MCP(stdio) ── server.py ──┬── worker.py (.venv,        build123d / OCCT)
                                   └── worker.py (.venv-smlib,  smlibpy / SMLib)
```

Each kernel runs as a persistent worker subprocess: variables survive between
`run_script` calls, like an interactive session. Dependencies stay isolated.

## Tools

| Tool | Purpose |
|---|---|
| `engines()` | list kernels, interpreters, worker status |
| `run_script(engine, code)` | execute Python; assign the final shape to `result`; returns stdout + metrics |
| `measure(engine)` | volume / bbox / solid count / faces / edges / validity |
| `export(engine, path, format)` | STEP / STL / DXF / glTF / OBJ (per kernel support) |
| `snapshot(engine, view)` | PNG: iso/front/back/left/right/top/bottom; `sheet` on build123d |
| `reset(engine)` | clear the session |

Engine aliases: `smlibpy` / `sm`, `build123d` / `b123d` / `b3d` / `occt`.
Relative paths resolve under `$CAD_OUT/<engine>/` (default `<repo>/out/<engine>/`).

## Typical session

```python
run_script("smlibpy", "from smlibpy import *\nresult = Box(80,60,10) - Cylinder(4,12)")
run_script("b3d",     "from build123d import *\nresult = Box(80,60,10) - Cylinder(4,12)")
measure("smlibpy")   # compare with measure("b3d")
snapshot("smlibpy", view="iso")
snapshot("b3d", view="sheet")
export("b3d", "part.step")
export("b3d", "part.dxf", format="dxf")
```

## Configuration

| Variable | Meaning | Default |
|---|---|---|
| `CAD_B123D_PYTHON` | interpreter with build123d | this interpreter |
| `CAD_SMLIBPY_PYTHON` | interpreter with smlibpy | `../smlibpy/venv`, `~/CAD/smlibpy/venv`, `python3` |
| `CAD_OUT` | output root | `<repo>/out` |

Register the server with any MCP client:

```json
{
  "mcpServers": {
    "cad": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/cad/mcp/server.py"],
      "env": {
        "CAD_B123D_PYTHON": "/path/to/.venv/bin/python",
        "CAD_SMLIBPY_PYTHON": "/path/to/.venv-smlib/bin/python",
        "CAD_OUT": "/path/to/output"
      }
    }
  }
}
```

## Running the e2e tests

`test_server.py` launches the real server and drives the whole tool contract
over stdio (initialize → tools/list → engines → run_script on both kernels →
measure → export → snapshot → reset). Stdlib only; exit code 0 = all checks
passed. Run it with the interpreter that has the `mcp` package:

```sh
CAD_B123D_PYTHON=/path/to/.venv/bin/python \
CAD_SMLIBPY_PYTHON=/path/to/.venv-smlib/bin/python \
    /path/to/.venv/bin/python mcp/test_server.py
```

The interpreters default to the same fallbacks as the server; output goes to a
temporary `CAD_OUT` that is removed afterwards. CI runs this in
`.github/workflows/ci.yml`.

## Adding a third kernel

1. Add `name -> interpreter` to `ENGINE_PYTHON` in `server.py`.
2. Add its export/snapshot branches in `worker.py`.
3. Add metric extraction to `engine_of` / `metrics_of` in `verify/measure.py`.

Kernels communicate over JSON lines in subprocesses, so nothing leaks between
their dependency trees.
