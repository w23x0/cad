#!/usr/bin/env python3
"""Run one CAD model script and emit metrics/exports as JSON.

Protocol
--------
The model script must expose either

    result = <shape>        # preferred
    def build(): return <shape>

A shape is any object with a numeric ``volume`` and a ``solids()`` method.
Supported engines today: build123d (OCCT) and smlibpy (SMLib).

CLI: measure.py MODEL.py --out DIR --json-out FILE
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
import traceback


def load_shape(path: str):
    ns = runpy.run_path(path, run_name="__model__")
    if "result" in ns and _is_shape(ns["result"]):
        return ns["result"]
    if callable(ns.get("build")):
        obj = ns["build"]()
        if _is_shape(obj):
            return obj
    candidates = [v for v in ns.values() if _is_shape(v)]
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit("model must define `result` or `build()` returning one shape")


def _is_shape(obj) -> bool:
    return (
        obj is not None
        and hasattr(obj, "volume")
        and callable(getattr(obj, "solids", None))
    )


def engine_of(shape) -> str:
    mod = type(shape).__module__
    if mod.startswith("smlibpy"):
        return "smlibpy"
    if hasattr(shape, "wrapped"):
        return "build123d"
    raise SystemExit(f"unsupported shape type: {type(shape)!r}")


def metrics_of(shape, engine: str) -> dict:
    if engine == "build123d":
        bb = shape.bounding_box()
        size = [float(bb.size.X), float(bb.size.Y), float(bb.size.Z)]
        valid = bool(shape.is_valid)
        faces = len(shape.faces())
        edges = len(shape.edges())
        c = shape.center()
        centroid = [float(c.X), float(c.Y), float(c.Z)]
    else:
        bb = shape.bbox()
        size = [float(bb.max[i] - bb.min[i]) for i in range(3)]
        valid = bool(shape.is_valid())
        faces = len(shape.faces())
        edges = len(shape.edges())
        c = shape.center()
        centroid = [float(c[0]), float(c[1]), float(c[2])]
    return {
        "engine": engine,
        "volume_mm3": float(shape.volume),
        "bbox_mm": size,
        "centroid_mm": centroid,
        "solids": len(shape.solids()),
        "faces": faces,
        "edges": edges,
        "valid": valid,
    }


def export_all(shape, engine: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    files: dict[str, str] = {}
    step = os.path.join(out_dir, "model.step")
    stl = os.path.join(out_dir, "model.stl")

    if engine == "build123d":
        from build123d import export_step, export_stl

        export_step(shape, step)
        export_stl(shape, stl)
        files["step"] = step
        files["stl"] = stl
        try:
            import subprocess

            from build123d import ExportSVG, LineType

            svg = ExportSVG(margin=3)
            svg.add_layer("visible", line_weight=0.35)
            svg.add_layer("hidden", line_weight=0.15, line_type=LineType.DASHED)
            visible, hidden = shape.project_to_viewport((80, -120, 70))
            svg.add_shape(visible, layer="visible")
            if hidden:
                svg.add_shape(hidden, layer="hidden")
            path = os.path.join(out_dir, "sheet.svg")
            svg.write(path)
            files["sheet"] = path
            png = os.path.join(out_dir, "sheet.png")
            try:
                import cairosvg

                cairosvg.svg2png(url=path, write_to=png, scale=3.0, background_color="white")
                files["sheet_png"] = png
            except Exception:
                conv = subprocess.run(
                    ["convert", "-density", "150", path, png],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if conv.returncode == 0 and os.path.exists(png):
                    files["sheet_png"] = png
                else:
                    files["sheet_png_error"] = (conv.stderr or "convert failed").strip()[-300:]
        except Exception as exc:  # rendering is best-effort
            files["sheet_error"] = f"{type(exc).__name__}: {exc}"
    else:
        from smlibpy import export_step as sm_export_step
        from smlibpy import export_stl as sm_export_stl
        from smlibpy import render as sm_render

        sm_export_step(shape, step)
        sm_export_stl(shape, stl)
        files["step"] = step
        files["stl"] = stl
        try:
            png = os.path.join(out_dir, "render.png")
            sm_render(shape, path=png, view="iso", size=(900, 700))
            files["render"] = png
        except Exception as exc:  # rendering is best-effort
            files["render_error"] = f"{type(exc).__name__}: {exc}"
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--out", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args()

    payload: dict = {"model": os.path.abspath(args.model), "ok": False}
    try:
        shape = load_shape(args.model)
        engine = engine_of(shape)
        payload.update(metrics_of(shape, engine))
        if not args.no_export:
            payload["files"] = export_all(shape, engine, args.out)
        payload["ok"] = True
    except Exception:
        payload["error"] = traceback.format_exc(limit=6)

    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    if not payload["ok"]:
        sys.stderr.write(payload["error"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
