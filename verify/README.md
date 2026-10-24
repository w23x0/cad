# verify — engine-agnostic CAD verification

One folder per part. One shared truth in `expected.json`. One implementation per
kernel. Everything runs, everything is compared.

```bash
.venv/bin/python verify/verify.py                 # all of bench/
.venv/bin/python verify/verify.py bench/03_flange
.venv/bin/python verify/verify.py --json
.venv/bin/python verify/verify.py --no-export     # metrics only
```

Exit codes: `0` all pass, `1` any failure, `2` no model folders found.
Suitable for CI.

## Folder contract

```
<part>/
  NOTES.md             design intent, dimensions, volume derivation
  expected.json        shared truth
  model_b123d.py       build123d (OCCT) implementation
  model_smlibpy.py     smlibpy (SMLib) implementation, optional
  out/<engine>/        generated STEP / STL / drawing / render
```

A model script only assigns `result = <shape>` (or defines `def build(): return shape`).
Measurement and export belong to the harness, not to the model.

## expected.json

```json
{
  "description": "80x60x10 plate ...",
  "metrics": {
    "volume_mm3": 43589.3807,
    "bbox_mm": [80, 60, 10],
    "solids": 1,
    "valid": true
  },
  "tolerance": { "volume_rel": 1e-6, "bbox_abs": 1e-6 }
}
```

`metrics` values may also be objects: `{"value": ..., "rel_tol": ...}`.
Optional `engine_metrics` records kernel-specific topology — face and edge
counts legitimately differ between kernels:

```json
"engine_metrics": { "build123d": { "faces": 15 } }
```

## What is checked

1. Each engine against `expected.json`: volume (relative), bbox (absolute),
   solid count, validity.
2. Engines against each other: volume, bbox, solid count, validity.
3. Exports: STEP + STL always; build123d additionally an SVG/PNG technical
   drawing with dashed hidden lines; smlibpy an isometric PNG render.

## Interpreters

| Variable | Meaning | Default |
|---|---|---|
| `CAD_B123D_PYTHON` | interpreter with build123d | current interpreter |
| `CAD_SMLIBPY_PYTHON` | interpreter with smlibpy | `../smlibpy/venv`, `~/CAD/smlibpy/venv`, `python3` |

Kernels live in their own virtualenvs and are called as subprocesses, so their
dependencies never collide.

## Adding an engine

Add `key -> (name, interpreter)` to `ENGINES` in `verify.py`, then add the
metric and export branches in `measure.py`.
