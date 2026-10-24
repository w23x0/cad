#!/usr/bin/env python3
"""Persistent geometry worker for one CAD kernel.

Speaks JSON lines on stdin/stdout. The server keeps one process per engine, so
variables survive between run_script calls, like an interactive session.

Requests:
    {"id": 1, "op": "exec",     "code": "result = Box(10,10,10)"}
    {"id": 2, "op": "measure"}
    {"id": 3, "op": "export",   "path": "...", "format": "step"}
    {"id": 4, "op": "snapshot", "path": "...", "view": "iso"}
    {"id": 5, "op": "reset"}
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_MEASURE = REPO_ROOT / "verify" / "measure.py"


def _load_measure():
    spec = importlib.util.spec_from_file_location("cad_measure", _MEASURE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


measure = _load_measure()

VIEWS = {
    "iso": ((80, -120, 70), (0, 0, 1)),
    "front": ((0, -200, 0), (0, 0, 1)),
    "back": ((0, 200, 0), (0, 0, 1)),
    "right": ((200, 0, 0), (0, 0, 1)),
    "left": ((-200, 0, 0), (0, 0, 1)),
    "top": ((0, 0, 200), (0, 1, 0)),
    "bottom": ((0, 0, -200), (0, 1, 0)),
}


def pick_shape(ns: dict):
    if measure._is_shape(ns.get("result")):
        return ns["result"]
    build = ns.get("build")
    if callable(build):
        obj = build()
        if measure._is_shape(obj):
            return obj
    for name in reversed(list(ns)):
        if name.startswith("_"):
            continue
        obj = ns[name]
        if measure._is_shape(obj):
            return obj
    return None


def describe(shape) -> dict | None:
    if shape is None:
        return None
    engine = measure.engine_of(shape)
    m = measure.metrics_of(shape, engine)
    m.pop("engine", None)
    return m


def export_shape(shape, path: Path, fmt: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt.lower().lstrip(".")
    engine = measure.engine_of(shape)

    if engine == "smlibpy":
        from smlibpy import (
            export_dxf,
            export_glb,
            export_gltf,
            export_obj,
            export_step,
            export_stl,
            export_usd,
        )

        table = {
            "step": export_step,
            "stp": export_step,
            "stl": export_stl,
            "dxf": export_dxf,
            "glb": export_glb,
            "gltf": export_gltf,
            "obj": export_obj,
            "usd": export_usd,
        }
        fn = table.get(fmt)
        if fn is None:
            raise ValueError(f"smlibpy does not support format {fmt!r}; try {sorted(table)}")
        fn(shape, str(path))
        return {"path": str(path), "format": fmt}

    from build123d import export_brep, export_gltf, export_obj, export_step, export_stl

    if fmt in ("dxf", "svg"):
        from build123d import ColorIndex, ExportDXF, ExportSVG, LineType

        origin, up = VIEWS["top"]
        visible, hidden = shape.project_to_viewport(origin, viewport_up=up)
        if fmt == "dxf":
            exp = ExportDXF()
            exp.add_layer("visible", color=ColorIndex.BY_LAYER)
            exp.add_layer("hidden", color=ColorIndex.BY_LAYER, line_type=LineType.DASHED)
            exp.add_shape(visible, layer="visible")
            if hidden:
                exp.add_shape(hidden, layer="hidden")
            exp.write(str(path))
        else:
            exp = ExportSVG(margin=3)
            exp.add_layer("visible", line_weight=0.35)
            exp.add_layer("hidden", line_weight=0.15, line_type=LineType.DASHED)
            exp.add_shape(visible, layer="visible")
            if hidden:
                exp.add_shape(hidden, layer="hidden")
            exp.write(str(path))
        return {"path": str(path), "format": fmt}

    table = {
        "step": export_step,
        "stp": export_step,
        "stl": export_stl,
        "brep": export_brep,
        "gltf": export_gltf,
        "obj": export_obj,
    }
    fn = table.get(fmt)
    if fn is None:
        raise ValueError(f"build123d does not support format {fmt!r}; try {sorted(table)}")
    fn(shape, str(path))
    return {"path": str(path), "format": fmt}


def snapshot_shape(shape, path: Path, view: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = measure.engine_of(shape)
    view = view.lower()

    if engine == "smlibpy":
        from smlibpy import render

        render(shape, path=str(path), view=view, size=(1000, 800))
        return {"path": str(path), "view": view}

    from build123d import ExportSVG, LineType

    if view == "sheet":
        origin, up = VIEWS["iso"]
    else:
        origin, up = VIEWS.get(view, VIEWS["iso"])
    svg = ExportSVG(margin=3)
    svg.add_layer("visible", line_weight=0.35)
    svg.add_layer("hidden", line_weight=0.15, line_type=LineType.DASHED)
    visible, hidden = shape.project_to_viewport(origin, viewport_up=up)
    svg.add_shape(visible, layer="visible")
    if hidden:
        svg.add_shape(hidden, layer="hidden")
    svg_path = path.with_suffix(".svg")
    svg.write(str(svg_path))
    try:
        import cairosvg

        cairosvg.svg2png(url=str(svg_path), write_to=str(path), scale=3.0)
    except Exception:
        import subprocess

        subprocess.run(["convert", "-density", "150", str(svg_path), str(path)], check=True)
    return {"path": str(path), "svg": str(svg_path), "view": view}


def respond(req: dict, fn):
    resp = {"id": req.get("id")}
    try:
        resp.update(fn())
        resp["ok"] = True
    except Exception:
        resp["ok"] = False
        resp["error"] = traceback.format_exc(limit=12)
    return resp


def main() -> int:
    ns: dict = {"__name__": "__cad_session__"}
    shape = None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        op = req.get("op")

        if op == "exec":
            out = io.StringIO()

            def _exec():
                nonlocal shape
                with contextlib.redirect_stdout(out):
                    exec(compile(req["code"], "<agent>", "exec"), ns)
                shape = pick_shape(ns)
                return {"stdout": out.getvalue(), "metrics": describe(shape)}

            resp = respond(req, _exec)
        elif op == "measure":
            resp = respond(req, lambda: {"metrics": describe(shape)})
        elif op == "export":
            if shape is None:
                resp = {"id": req.get("id"), "ok": False, "error": "no shape yet; run_script first"}
            else:
                path = Path(req["path"]).expanduser()
                resp = respond(req, lambda: {"file": export_shape(shape, path, req.get("format", "step"))})
        elif op == "snapshot":
            if shape is None:
                resp = {"id": req.get("id"), "ok": False, "error": "no shape yet; run_script first"}
            else:
                path = Path(req["path"]).expanduser()
                resp = respond(req, lambda: {"file": snapshot_shape(shape, path, req.get("view", "iso"))})
        elif op == "reset":
            ns = {"__name__": "__cad_session__"}
            shape = None
            resp = {"id": req.get("id"), "ok": True, "reset": True}
        else:
            resp = {"id": req.get("id"), "ok": False, "error": f"unknown op {op!r}"}

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
