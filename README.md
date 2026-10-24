# cad-harness

Two independent CAD kernels, one verification contract, one MCP interface — built for AI agents that must check their own geometry.

A single kernel can produce a model that looks fine but has the wrong volume or a broken solid. This harness makes that visible: every part is implemented **twice** (SMLib and OCCT), checked against **hand-computed** truth, and compared kernel-to-kernel.

```
bench/<part>/          NOTES.md + expected.json + model_b123d.py + model_smlibpy.py
verify/                engine-agnostic verifier (metrics + cross-check + exports)
mcp/                   one MCP server: run_script / measure / export / snapshot / reset
```

## Why two kernels

| | Kernel | Package |
|---|---|---|
| Primary | SMLib (NURBS / B-rep) | [`smlibpy`](https://pypi.org/project/smlibpy/) |
| Cross-check | OCCT | [`build123d`](https://pypi.org/project/build123d/) |

They share no geometry code. If volume, bounding box, solid count and validity agree within `1e-6`, the model is very likely right. Disagreement points at a kernel bug or an ambiguous design.

## Quick start

```bash
git clone <this repo> && cd cad-harness
uv venv --python 3.13 .venv
uv pip install build123d ezdxf trimesh cairosvg mcp

# optional, in a separate venv (smlibpy targets a different Python):
python3 -m venv .venv-smlib && .venv-smlib/bin/pip install smlibpy

export CAD_B123D_PYTHON="$PWD/.venv/bin/python"
export CAD_SMLIBPY_PYTHON="$PWD/.venv-smlib/bin/python"

.venv/bin/python verify/verify.py
```

Output:

```
folder               engine             volume                   bbox  solids  valid  status
01_plate             build123d       43589.381               80x60x10       1   True  ok
01_plate             smlibpy         43589.381               80x60x10       1   True  ok
...
```

Exit code is `0` only when all engines match `expected.json` **and** each other.

## `expected.json`

```json
{
  "description": "80x60x10 plate, 4x M8 holes, 30x20x4 pocket",
  "metrics": {
    "volume_mm3": 43589.38070170253,
    "bbox_mm": [80, 60, 10],
    "solids": 1,
    "valid": true
  },
  "tolerance": { "volume_rel": 1e-6, "bbox_abs": 1e-6 }
}
```

Write the volume from the **hand calculation**, not from a run. Optional
`engine_metrics` records kernel-specific topology (face/edge counts legitimately differ).

Models only expose `result = <shape>` (or `def build()`); the harness does the
measuring and exporting. Generated files go to `bench/<part>/out/<engine>/`:
STEP + STL always, plus an SVG/PNG technical drawing for build123d and an
isometric render for smlibpy.

## MCP server

```bash
.venv/bin/python mcp/server.py        # stdio
```

Tools: `engines`, `run_script`, `measure`, `export`, `snapshot`, `reset`.

```text
run_script("smlibpy", "from smlibpy import *\nresult = Box(80,60,10) - Cylinder(4,12)")
run_script("b3d",     "from build123d import *\nresult = Box(80,60,10) - Cylinder(4,12)")
measure("smlibpy")    # compare volume_mm3 / bbox_mm / solids
snapshot("b3d", view="sheet")
export("b3d", "part.step")
```

Each engine is a persistent worker subprocess: variables survive between calls,
dependencies stay isolated. `engine` accepts `smlibpy`/`sm` and
`build123d`/`b123d`/`b3d`/`occt`.

Client config (Claude Desktop / Claude Code, Codex, opencode, omp):

```json
{
  "mcpServers": {
    "cad": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/cad-harness/mcp/server.py"],
      "env": {
        "CAD_B123D_PYTHON": "/path/to/.venv/bin/python",
        "CAD_SMLIBPY_PYTHON": "/path/to/.venv-smlib/bin/python",
        "CAD_OUT": "/path/to/output"
      }
    }
  }
}
```

## Adding a part

1. `bench/NN_name/` with `NOTES.md` (dimensions, build order, hand-computed volume).
2. `model_b123d.py` and `model_smlibpy.py`, both assigning `result`.
3. Run the verifier; when both kernels agree, put the hand value in `expected.json`.

Keep parts small (seconds, not minutes). See `bench/README.md` and the three seeds:
plate, L bracket, flange.

## License

MIT. Dependencies keep their own licenses: build123d (Apache-2.0), smlibpy
(MIT AND Apache-2.0 AND OFL-1.1), OCCT (LGPL-2.1 with exception).
