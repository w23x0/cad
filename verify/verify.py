#!/usr/bin/env python3
"""Engine-agnostic verification for CAD model folders.

Each folder under bench/ (or any folder passed on the CLI) looks like:

    NOTES.md
    expected.json
    model_b123d.py      # build123d / OCCT
    model_smlibpy.py    # smlibpy / SMLib (optional)

`expected.json` holds the shared truth; every engine must match it, and the
engines are additionally compared against each other. Exit code 0 only when
all checks pass.

Usage:
    ~/.venv/bin/python verify/verify.py [FOLDER ...] [--no-export]
    ~/.venv/bin/python verify/verify.py --json

Environment:
    CAD_B123D_PYTHON    interpreter with build123d (default: this interpreter)
    CAD_SMLIBPY_PYTHON  interpreter with smlibpy (default: ../smlibpy/venv, then python3)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASURE = str(REPO_ROOT / "verify" / "measure.py")


def _smlibpy_python() -> str:
    candidates = [
        os.environ.get("CAD_SMLIBPY_PYTHON"),
        str(REPO_ROOT.parent / "smlibpy" / "venv" / "bin" / "python"),
        str(Path.home() / "CAD" / "smlibpy" / "venv" / "bin" / "python"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return "python3"


ENGINES = {
    "b123d": ("build123d", os.environ.get("CAD_B123D_PYTHON") or sys.executable),
    "smlibpy": ("smlibpy", _smlibpy_python()),
}

DEFAULT_TOL = {
    "volume_rel": 1e-6,
    "bbox_abs": 1e-6,
    "volume_abs": 1e-6,
    "centroid_abs": 1e-6,
    "interference_abs": 1e-9,
}


def find_folders(paths):
    folders = []
    for p in paths:
        if os.path.isfile(os.path.join(p, "expected.json")):
            folders.append(os.path.abspath(p))
            continue
        for expected in sorted(glob.glob(os.path.join(p, "*", "expected.json"))):
            folders.append(os.path.dirname(expected))
    return folders


def run_model(model_path, engine_key, out_dir, do_export):
    python = ENGINES[engine_key][1]
    if not os.path.isfile(python):
        return {"ok": False, "error": f"interpreter not found: {python}"}
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    cmd = [python, MEASURE, model_path, "--out", out_dir, "--json-out", tmp.name]
    if not do_export:
        cmd.append("--no-export")
    proc = subprocess.run(cmd, cwd=os.path.dirname(model_path), capture_output=True, text=True)
    try:
        with open(tmp.name, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        payload = {"ok": False, "error": (proc.stderr or proc.stdout or "no output")[-2000:]}
    finally:
        os.unlink(tmp.name)
    payload.setdefault("ok", False)
    if not payload["ok"] and proc.returncode != 0 and "error" not in payload:
        payload["error"] = proc.stderr[-2000:]
    return payload


def rel_err(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1e-12)


def check_expected(metrics, expected, tol):
    problems = []
    m = expected.get("metrics", expected)
    v = m.get("volume_mm3")
    if v is not None:
        tgt = v["value"] if isinstance(v, dict) else float(v)
        if rel_err(metrics["volume_mm3"], tgt) > tol["volume_rel"] and abs(metrics["volume_mm3"] - tgt) > tol["volume_abs"]:
            problems.append(f"volume {metrics['volume_mm3']:.6f} != {tgt:.6f}")
    bb = m.get("bbox_mm")
    if bb is not None:
        tgt = bb["value"] if isinstance(bb, dict) else bb
        for i, axis in enumerate("XYZ"):
            if abs(metrics["bbox_mm"][i] - float(tgt[i])) > tol["bbox_abs"]:
                problems.append(f"bbox {axis} {metrics['bbox_mm'][i]:.6f} != {float(tgt[i]):.6f}")
    ce = m.get("centroid_mm")
    if ce is not None:
        tgt = ce["value"] if isinstance(ce, dict) else ce
        for i, axis in enumerate("XYZ"):
            if abs(metrics["centroid_mm"][i] - float(tgt[i])) > tol["centroid_abs"]:
                problems.append(
                    f"centroid {axis} {metrics['centroid_mm'][i]:.6f} != {float(tgt[i]):.6f}"
                )
    im = m.get("interference_mm3")
    if im is not None:
        tgt = im["value"] if isinstance(im, dict) else im
        if abs(metrics.get("interference_mm3", 0.0) - float(tgt)) > tol["interference_abs"]:
            problems.append(
                f"interference {metrics.get('interference_mm3')} != {float(tgt)}"
            )
    for key in ("solids", "faces", "edges"):
        if key in m:
            tgt = m[key]["value"] if isinstance(m[key], dict) else m[key]
            if metrics[key] != tgt:
                problems.append(f"{key} {metrics[key]} != {tgt}")
    if "valid" in m:
        tgt = m["valid"]["value"] if isinstance(m["valid"], dict) else m["valid"]
        if bool(metrics["valid"]) != bool(tgt):
            problems.append(f"valid {metrics['valid']} != {tgt}")
    return problems


def check_cross(metrics_a, metrics_b, tol):
    problems = []
    if rel_err(metrics_a["volume_mm3"], metrics_b["volume_mm3"]) > tol["volume_rel"]:
        problems.append("cross volume mismatch")
    for i, axis in enumerate("XYZ"):
        if abs(metrics_a["bbox_mm"][i] - metrics_b["bbox_mm"][i]) > tol["bbox_abs"]:
            problems.append(f"cross bbox {axis} mismatch")
        if abs(metrics_a["centroid_mm"][i] - metrics_b["centroid_mm"][i]) > tol["centroid_abs"]:
            problems.append(f"cross centroid {axis} mismatch")
    if "interference_mm3" in metrics_a and "interference_mm3" in metrics_b:
        if abs(metrics_a["interference_mm3"] - metrics_b["interference_mm3"]) > tol["interference_abs"]:
            problems.append("cross interference mismatch")
    if metrics_a["solids"] != metrics_b["solids"]:
        problems.append("cross solids mismatch")
    if metrics_a["valid"] != metrics_b["valid"]:
        problems.append("cross validity mismatch")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=[os.path.join(REPO_ROOT, "bench")])
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args()

    folders = find_folders(args.paths)
    if not folders:
        print("no model folders found", file=sys.stderr)
        return 2

    report = {"folders": [], "ok": True, "checked": 0, "failed": 0}
    for folder in folders:
        with open(os.path.join(folder, "expected.json"), encoding="utf-8") as fh:
            expected = json.load(fh)
        tol = dict(DEFAULT_TOL)
        tol.update(expected.get("tolerance", {}))
        engine_metrics = expected.get("engine_metrics", {})

        results = {}
        for engine_key, (engine_name, _) in ENGINES.items():
            model = os.path.join(folder, f"model_{engine_key}.py")
            if not os.path.isfile(model):
                continue
            out_dir = os.path.join(folder, "out", engine_name)
            payload = run_model(model, engine_key, out_dir, not args.no_export)
            results[engine_name] = payload

        entry = {"folder": os.path.basename(folder), "engines": {}, "problems": []}
        if not results:
            entry["problems"].append("no model_<engine>.py found")
        for engine_name, payload in results.items():
            if not payload.get("ok"):
                entry["problems"].append(f"{engine_name}: {payload.get('error', 'failed')}")
                continue
            problems = check_expected(payload, expected, tol)
            extra = engine_metrics.get(engine_name, {})
            for key, tgt in extra.items():
                if payload.get(key) != tgt:
                    problems.append(f"{engine_name} {key} {payload.get(key)} != {tgt}")
            entry["engines"][engine_name] = {
                "volume_mm3": payload["volume_mm3"],
                "bbox_mm": payload["bbox_mm"],
                "solids": payload["solids"],
                "faces": payload["faces"],
                "valid": payload["valid"],
                "problems": problems,
            }
            entry["problems"].extend(f"{engine_name}: {p}" for p in problems)

        ok_payloads = [p for p in results.values() if p.get("ok")]
        if len(ok_payloads) >= 2:
            cross = check_cross(ok_payloads[0], ok_payloads[1], tol)
            entry["problems"].extend(f"cross: {p}" for p in cross)

        entry["ok"] = not entry["problems"]
        report["ok"] = report["ok"] and entry["ok"]
        report["checked"] += 1
        report["failed"] += 0 if entry["ok"] else 1
        report["folders"].append(entry)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{'folder':<20} {'engine':<10} {'volume':>14} {'bbox':>22} {'solids':>7} {'valid':>6}  status")
        for entry in report["folders"]:
            if not entry["engines"]:
                print(f"{entry['folder']:<20} {'-':<10} {'-':>14} {'-':>22} {'-':>7} {'-':>6}  FAIL")
            for engine_name, r in entry["engines"].items():
                bbox = "x".join(f"{v:g}" for v in r["bbox_mm"])
                status = "ok" if not r["problems"] else "FAIL"
                print(f"{entry['folder']:<20} {engine_name:<10} {r['volume_mm3']:>14.3f} {bbox:>22} {r['solids']:>7} {str(r['valid']):>6}  {status}")
            for p in entry["problems"]:
                print(f"  - {p}")
        print(f"\n{report['checked']} folders, {report['failed']} failed")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
