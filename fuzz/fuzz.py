#!/usr/bin/env python3
"""Cross-kernel parity fuzzer: random CSG programs, build123d (OCCT) vs smlibpy (SMLib).

For each case a shared random parameter set describes a small CSG design
(4-8 primitives combined by 3-6 union/subtract/split operations).  The SAME
parameters are rendered twice -- model_b123d.py and model_smlibpy.py --
differing only in the import line, plus the engine-specific spelling of
`split` calls (whose plane geometry and kept side come from the same shared
parameters; smlibpy `split(part, plane, keep="above")` vs b123d
`split(part, bisect_by=plane, keep=Keep.TOP)` -- probe-verified to mean the
same side), so any metric difference is a kernel divergence, not a modeling
difference.  Each model runs through the harness/verify/measure.py protocol
(same as verify.py uses) and the resulting metrics are compared.

Classifications per case:
    match        all compared metrics agree within tolerance
    divergence   volume/bbox/solids/valid differ beyond tolerance  (a finding)
    engine-error one kernel raised, produced nothing, or timed out    (a finding)
    degenerate   result volume ~0 on both kernels; comparison skipped

Divergences are auto-tagged against the known catalogue (fuzz/FINDINGS.md):
    F-1-family   relative volume drift <= 5e-5 on a case whose unioned
                 primitives AABB-overlap (smlibpy overlapping-boolean band)
    F-5-family   any bbox mismatch (OCCT bounding_box not tight, cf. FZ-2)
    NEW          anything else -- minimized by hand, see FINDINGS.md

Usage:
    envs/cad/bin/python fuzz/fuzz.py                       # default seed, 30 cases
    envs/cad/bin/python fuzz/fuzz.py --seed 42 --cases 10 --keep
    envs/cad/bin/python fuzz/fuzz.py --seed 42 --only 7 --keep   # regenerate one case

Exit code: 0 when all cases match; 1 when any divergence or engine-error
(suppress with --no-strict).  Machine-readable results go to fuzz/report.json.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASURE = str(REPO_ROOT / "verify" / "measure.py")
FUZZ_DIR = REPO_ROOT / "fuzz"
CASES_DIR = FUZZ_DIR / "cases"

DEGENERATE_VOLUME_MM3 = 1e-3  # below this (on both kernels) a case is degenerate
ROT_ANGLES = (0, 45, 90, 135, 180, 225, 270, 315)


def _b123d_python() -> str:
    candidates = [
        os.environ.get("CAD_B123D_PYTHON"),
        str(REPO_ROOT.parent / "envs" / "cad" / "bin" / "python"),
        sys.executable,
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return "python3"


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
    "b123d": ("build123d", _b123d_python()),
    "smlibpy": ("smlibpy", _smlibpy_python()),
}


# --------------------------------------------------------------------------
# Parameter generator
# --------------------------------------------------------------------------

def _rotated_half_extents(hx: float, hy: float, hz: float, axis: str, deg: float):
    """Half extents of a box with half-extents (hx, hy, hz) after rotating
    `deg` degrees about a single world axis (the fuzzer only rotates about
    one axis per primitive, so this is exact)."""
    if deg == 0:
        return hx, hy, hz
    r = math_radians(deg)
    c, s = abs(cos(r)), abs(sin(r))
    if axis == "Z":
        return hx * c + hy * s, hx * s + hy * c, hz
    if axis == "X":
        return hx, hy * c + hz * s, hy * s + hz * c
    return hx * c + hz * s, hy, hx * s + hz * c  # Y


# tiny local trig to keep the module import-free of anything unusual
def math_radians(deg):
    import math
    return math.radians(deg)


def cos(x):
    import math
    return math.cos(x)


def sin(x):
    import math
    return math.sin(x)


def make_primitive(rng: random.Random, containment: float = 50.0) -> dict:
    """One randomly sized, rotated and translated primitive, guaranteed to fit
    inside [-containment, containment]^3.  Translation is sampled in
    [-40, 40] and clamped only where containment would be violated.

    The `revolve` kind is a partial-angle solid of revolution: a rectangular or
    right-trapezoid polygon profile on the XZ plane (local x = radius 8..20,
    local y = height within +-8), revolved about Axis.Z by 90/180/270/300
    degrees.  Both kernels start the sweep at the profile phase (+X) and go
    counter-clockwise (probe r1: bbox min (0,0,2), max (15,15,6) identical);
    its bbox is bounded conservatively by the full ring (radius r1)."""
    kind = rng.choice(["box", "cylinder", "sphere", "cone", "revolve"])
    if kind == "box":
        w, d, h = (rng.randint(8, 20) for _ in range(3))
        args = (w, d, h)
        half = (w / 2, d / 2, h / 2)
    elif kind == "cylinder":
        r, h = rng.randint(3, 10), rng.randint(8, 24)
        args = (r, h)
        half = (float(r), float(r), h / 2)
    elif kind == "sphere":
        r = rng.randint(4, 12)
        args = (r,)
        half = (float(r), float(r), float(r))
    elif kind == "cone":
        r1, r2, h = rng.randint(3, 10), rng.randint(3, 10), rng.randint(8, 24)
        # FZ-1 noise removal: Cone(r, r, h) is a construction-domain error on
        # b123d (Standard_DomainError) while smlibpy normalizes it to a
        # cylinder -- a classified semantic difference we no longer re-measure.
        # Integer radii make |r1-r2|/max(r1,r2) either 0 or >= 0.1, so this
        # degenerates to "resample until r1 != r2".
        while abs(r1 - r2) / max(r1, r2) < 1e-3:
            r2 = rng.randint(3, 10)
        args = (r1, r2, h)
        m = float(max(r1, r2))
        half = (m, m, h / 2)
    else:  # revolve: polygon profile on XZ plane, partial angle about Axis.Z
        r0 = rng.randint(8, 12)                     # inner radius, keeps the axis clear
        r1 = r0 + rng.randint(4, 8)                 # outer radius 12..20
        h = rng.randint(4, 12)                      # profile height
        zc = round(rng.uniform(-(8 - h / 2), 8 - h / 2), 2)  # keep z within +-8
        z0, z1 = round(zc - h / 2, 2), round(zc + h / 2, 2)
        if rng.random() < 0.5:                      # rectangle vs right-trapezoid
            r_top = r1
        else:
            r_top = round(rng.uniform(r0 + 1.0, r1 - 1.0), 2)
        angle = rng.choice([90, 180, 270, 300])
        args = (r0, r1, z0, z1, r_top, angle)
        half = (float(r1), float(r1), h / 2)

    axis = rng.choice("XYZ")
    deg = rng.choice(ROT_ANGLES)
    hx, hy, hz = _rotated_half_extents(*half, axis=axis, deg=deg)
    lim = (min(40.0, containment - hx), min(40.0, containment - hy), min(40.0, containment - hz))
    t = []
    for lo_hi in lim:
        lo_hi = max(lo_hi, 0.0)
        t.append(round(max(-lo_hi, min(lo_hi, rng.uniform(-40.0, 40.0))), 2))

    return {
        "kind": kind,
        "args": list(args),
        "t": t,
        "rot_axis": None if deg == 0 else axis,
        "rot_deg": deg,
        "half": [hx, hy, hz],
    }


SPLIT_Z_DIRS = ((0, 0, 1), (1, 0, 1), (1, 0, 0))
# x_dir chosen perpendicular to each z_dir (b123d/smlibpy Plane(origin, x_dir, z_dir))
SPLIT_X_DIR = {(0, 0, 1): (1, 0, 0), (1, 0, 1): (1, 0, -1), (1, 0, 0): (0, 1, 0)}


def make_split_params(rng: random.Random, prims: list) -> dict:
    """A plane-split op applied to the accumulated result.  The plane origin is
    placed inside a reference primitive (base or latest), so it really cuts
    material; z_dir is axis-aligned or 45-degree; the kept side is recorded
    kernel-neutrally ("above" = the side the plane z_dir points to) and spelled
    per engine by the renderer (probe-verified mapping:
    smlibpy keep="above" <-> b123d Keep.TOP, "below" <-> Keep.BOTTOM).
    keep="both" is deliberately NOT generated: smlibpy returns a tuple whose
    halves re-fuse into 1 solid while b123d Keep.BOTH keeps a 2-solid Compound
    (probe s5) -- a topology semantic difference, not comparable as-is."""
    ref = prims[0] if rng.random() < 0.5 else prims[-1]
    origin = [round(ref["t"][k] + rng.uniform(-0.6, 0.6) * ref["half"][k], 2)
              for k in range(3)]
    z_dir = rng.choice(SPLIT_Z_DIRS)
    return {
        "kind": "split",
        "origin": origin,
        "x_dir": list(SPLIT_X_DIR[tuple(z_dir)]),
        "z_dir": list(z_dir),
        "keep": rng.choice(["above", "below"]),
    }


def gen_case_params(seed: int, index: int) -> dict:
    rng = random.Random(f"{seed}:case:{index:03d}")
    n_ops = rng.randint(3, 6)  # number of boolean/split operations
    base = make_primitive(rng)
    prims = [base]
    ops = []
    next_prim = 1
    n_bool_done = 0
    for _ in range(n_ops):
        if rng.random() < 0.18:  # plane split consumes no primitive
            ops.append(make_split_params(rng, prims))
            continue
        # anchor the new primitive near the base or the previous one so most
        # operations actually interact (misses still happen -- that is fine)
        anchor = base["t"] if n_bool_done == 0 or rng.random() < 0.5 else prims[-1]["t"]
        p = make_primitive(rng)
        lim = p["half"]
        p["t"] = [
            round(max(-(50.0 - lim[k]), min(50.0 - lim[k], anchor[k] + rng.uniform(-15.0, 15.0))), 2)
            for k in range(3)
        ]
        prims.append(p)
        ops.append({"kind": rng.choice(["union", "subtract"]), "prim": next_prim})
        next_prim += 1
        n_bool_done += 1
    return {"seed": seed, "index": index, "n_ops": n_ops, "prims": prims, "ops": ops}


# --------------------------------------------------------------------------
# Model rendering (identical statements for both engines, import differs)
# --------------------------------------------------------------------------

def _prim_expr(p: dict) -> str:
    tx, ty, tz = p["t"]
    loc = f"Pos({tx}, {ty}, {tz})"
    if p["rot_axis"] is not None:
        r = [0, 0, 0]
        r["XYZ".index(p["rot_axis"])] = p["rot_deg"]
        loc += f" * Rot({r[0]}, {r[1]}, {r[2]})"
    if p["kind"] == "revolve":
        # identical statement on both kernels: probe-verified that
        # revolve(profile, Axis.Z, angle) shares signature, start phase (+X)
        # and sweep direction (CCW) between smlibpy and build123d
        r0, r1, z0, z1, r_top, angle = p["args"]
        pts = f"({r0}, {z0}), ({r1}, {z0}), ({r_top}, {z1}), ({r0}, {z1})"
        return f"{loc} * revolve(Plane.XZ * Polygon({pts}), Axis.Z, {angle})"
    ctor = {"box": "Box", "cylinder": "Cylinder", "sphere": "Sphere", "cone": "Cone"}[p["kind"]]
    args = ", ".join(str(a) for a in p["args"])
    return f"{loc} * {ctor}({args})"


def _split_stmt(sp: dict, engine_key: str) -> str:
    """Engine-specific spelling of one identical plane split.  The plane origin,
    directions and the kept side ("above" = side z_dir points to) come from the
    shared parameters; only the API spelling differs (probe s1/s2: smlibpy
    keep="above" == b123d Keep.TOP, exact equal volumes incl. a 45-degree
    plane).  keep="both" is never generated -- see make_split_params."""
    ox, oy, oz = sp["origin"]
    xd, zd = sp["x_dir"], sp["z_dir"]
    plane = (f"Plane(({ox}, {oy}, {oz}), "
             f"({xd[0]}, {xd[1]}, {xd[2]}), ({zd[0]}, {zd[1]}, {zd[2]}))")
    if engine_key == "smlibpy":
        return f"result = split(result, {plane}, keep=\"{sp['keep']}\")"
    keep = "Keep.TOP" if sp["keep"] == "above" else "Keep.BOTTOM"
    return f"result = split(result, bisect_by={plane}, keep={keep})"


def render_model(params: dict, engine_key: str) -> str:
    lines = [
        f"# Auto-generated by harness/fuzz/fuzz.py -- seed={params['seed']} case={params['index']:03d} engine={ENGINES[engine_key][0]}",
        f"from {ENGINES[engine_key][0]} import *",
        "",
    ]
    for i, p in enumerate(params["prims"]):
        lines.append(f"p{i} = {_prim_expr(p)}")
    lines.append("")
    lines.append("result = p0")
    for op in params["ops"]:
        if op["kind"] == "split":
            lines.append(_split_stmt(op, engine_key))
        else:
            i = op["prim"]
            sym = "+" if op["kind"] == "union" else "-"
            lines.append(f"result = result {sym} p{i}")
    lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Runner (measure.py protocol, cf. verify.py run_model)
# --------------------------------------------------------------------------

def run_engine(model_path: Path, engine_key: str, timeout: float) -> dict:
    python = ENGINES[engine_key][1]
    if not os.path.isfile(python):
        return {"ok": False, "error": f"interpreter not found: {python}"}
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    cmd = [python, MEASURE, str(model_path), "--out", str(model_path.parent / "out" / engine_key),
           "--json-out", tmp.name, "--no-export"]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(model_path.parent), capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        # a kernel that hangs is a finding of its own -- flagged separately
        return {"ok": False, "error": f"timeout after {timeout:g}s (hang)",
                "timeout": True, "runtime_s": time.monotonic() - t0}
    runtime = time.monotonic() - t0
    try:
        with open(tmp.name, encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        payload = {"ok": False, "error": (proc.stderr or proc.stdout or "no output")[-2000:]}
    finally:
        os.unlink(tmp.name)
    payload.setdefault("ok", False)
    payload["runtime_s"] = round(runtime, 3)
    if not payload["ok"] and "error" not in payload:
        payload["error"] = (proc.stderr or "unknown error")[-2000:]
    return payload


def compare(ma: dict, mb: dict, tol: float) -> list[str]:
    """Cross-kernel comparison of two ok payloads.  Faces/edges are recorded
    but deliberately not compared: topology counts legitimately differ between
    kernels; volume, bbox, solid count and validity must not."""
    problems = []
    va, vb = ma["volume_mm3"], mb["volume_mm3"]
    rel = abs(va - vb) / max(abs(va), abs(vb), 1e-12)
    if rel > tol:
        problems.append(f"volume rel diff {rel:.3e} (b123d={va:.9f}, smlibpy={vb:.9f}, tol={tol:g})")
    for i, axis in enumerate("XYZ"):
        d = abs(ma["bbox_mm"][i] - mb["bbox_mm"][i])
        if d > tol:
            problems.append(f"bbox {axis} abs diff {d:.3e} (b123d={ma['bbox_mm'][i]:.9f}, "
                            f"smlibpy={mb['bbox_mm'][i]:.9f}, tol={tol:g})")
    if ma["solids"] != mb["solids"]:
        problems.append(f"solids {ma['solids']} != {mb['solids']}")
    if bool(ma["valid"]) != bool(mb["valid"]):
        problems.append(f"valid {ma['valid']} != {mb['valid']}")
    return problems


# --------------------------------------------------------------------------
# Divergence classifier (known-issue tagging, cf. fuzz/FINDINGS.md)
# --------------------------------------------------------------------------

F1_REL_LIMIT = 5e-5  # observed smlibpy overlapping-boolean volume-drift band


def _prim_aabb(p: dict) -> list:
    t, h = p["t"], p["half"]
    return [(t[k] - h[k], t[k] + h[k]) for k in range(3)]


def _aabbs_overlap(a: list, b: list, eps: float = 1e-9) -> bool:
    return all(a[k][0] <= b[k][1] + eps and b[k][0] <= a[k][1] + eps for k in range(3))


def _has_overlapping_union(params: dict) -> bool:
    """True if any union in the op chain joins two primitives whose conservative
    AABBs intersect (heuristic: rotated half-extents + containment clamp)."""
    placed = [_prim_aabb(params["prims"][0])]
    for op in params["ops"]:
        if op["kind"] == "split":
            continue
        box = _prim_aabb(params["prims"][op["prim"]])
        if op["kind"] == "union" and any(_aabbs_overlap(box, q) for q in placed):
            return True
        placed.append(box)
    return False


def classify_divergence(params: dict, rel: float, problems: list) -> list:
    """Tag a divergence against the known catalogue.  bbox mismatches are the
    OCCT not-tight bounding_box family (F-5/FZ-2); small relative volume drift
    on overlapping-union cases is the smlibpy F-1 band; everything else is NEW
    and must be minimized by hand."""
    tags = []
    if any(p.startswith("bbox") for p in problems):
        tags.append("F-5-family")
    if (any(p.startswith("volume") for p in problems)
            and rel <= F1_REL_LIMIT
            and _has_overlapping_union(params)):
        tags.append("F-1-family")
    return tags or ["NEW"]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261027)
    ap.add_argument("--cases", type=int, default=30)
    ap.add_argument("--tol", type=float, default=1e-6, help="relative volume / absolute bbox tolerance (mm)")
    ap.add_argument("--timeout", type=float, default=30.0, help="per-kernel timeout in seconds")
    ap.add_argument("--keep", action="store_true", help="keep case directories under fuzz/cases/")
    ap.add_argument("--only", default="", help="comma-separated case indices to (re)run, e.g. 3,7,12")
    ap.add_argument("--strict", dest="strict", action="store_true", default=True,
                    help="exit 1 on divergence/engine-error (default)")
    ap.add_argument("--no-strict", dest="strict", action="store_false",
                    help="always exit 0; report findings without failing")
    args = ap.parse_args()

    only = {int(x) for x in args.only.split(",") if x.strip()} if args.only else None
    indices = sorted(only) if only else list(range(1, args.cases + 1))

    report = {
        "seed": args.seed,
        "tol": args.tol,
        "timeout_s": args.timeout,
        "cases": [],
        "summary": {},
    }
    counts = {"match": 0, "divergence": 0, "engine-error": 0, "degenerate": 0}
    kind_hist: dict[str, int] = {}
    tag_hist: dict[str, int] = {}

    print(f"fuzz: seed={args.seed} tol={args.tol:g} timeout={args.timeout:g}s cases={len(indices)}"
          f"  (b123d: {ENGINES['b123d'][1]}; smlibpy: {ENGINES['smlibpy'][1]})")
    CASES_DIR.mkdir(parents=True, exist_ok=True)

    for idx in indices:
        params = gen_case_params(args.seed, idx)
        case_name = f"seed{args.seed}_case{idx:03d}"
        case_dir = CASES_DIR / case_name
        case_dir.mkdir(parents=True, exist_ok=True)

        entry = {"index": idx, "name": case_name, "params": params,
                 "status": "match", "problems": [], "engines": {}}

        payloads = {}
        for engine_key in ENGINES:
            model_path = case_dir / f"model_{engine_key}.py"
            model_path.write_text(render_model(params, engine_key), encoding="utf-8")
            payloads[engine_key] = run_engine(model_path, engine_key, args.timeout)

        for engine_key, payload in payloads.items():
            if payload.get("ok"):
                entry["engines"][engine_key] = {
                    "ok": True,
                    "volume_mm3": payload["volume_mm3"],
                    "bbox_mm": payload["bbox_mm"],
                    "solids": payload["solids"],
                    "faces": payload.get("faces"),
                    "edges": payload.get("edges"),
                    "valid": payload["valid"],
                    "runtime_s": payload["runtime_s"],
                }
            else:
                entry["engines"][engine_key] = {
                    "ok": False,
                    "error": (payload.get("error") or "unknown")[-800:],
                    "timeout": bool(payload.get("timeout")),
                    "runtime_s": payload.get("runtime_s"),
                }

        if not all(p.get("ok") for p in payloads.values()):
            entry["status"] = "engine-error"
            for engine_key, payload in payloads.items():
                if not payload.get("ok"):
                    tail = (payload.get("error") or "unknown").strip().splitlines()
                    brief = tail[-1] if tail else "unknown"
                    kind = f"engine-error:{engine_key}"
                    kind_hist[kind] = kind_hist.get(kind, 0) + 1
                    entry["problems"].append(f"{engine_key}: {brief[:160]}")
        else:
            ma, mb = payloads["b123d"], payloads["smlibpy"]
            if max(ma["volume_mm3"], mb["volume_mm3"]) < DEGENERATE_VOLUME_MM3:
                entry["status"] = "degenerate"
            else:
                problems = compare(ma, mb, args.tol)
                entry["problems"] = problems
                entry["status"] = "divergence" if problems else "match"
                if problems:
                    va, vb = ma["volume_mm3"], mb["volume_mm3"]
                    rel = abs(va - vb) / max(abs(va), abs(vb), 1e-12)
                    tags = classify_divergence(params, rel, problems)
                    entry["rel_volume_diff"] = rel
                    entry["tags"] = tags
                    for tag in tags:
                        tag_hist[tag] = tag_hist.get(tag, 0) + 1
                for p in problems:
                    kind = p.split()[0] + ("." + p.split()[1] if p.startswith("bbox") else "")
                    kind_hist[kind] = kind_hist.get(kind, 0) + 1

        counts[entry["status"]] += 1
        report["cases"].append(entry)

        vol_b = entry["engines"].get("b123d", {}).get("volume_mm3")
        vol_s = entry["engines"].get("smlibpy", {}).get("volume_mm3")
        vol_txt = (
            "n/a"
            if vol_b is None or vol_s is None
            else f"vol {vol_b:.3f}/{vol_s:.3f}"
        )
        flag = "" if entry["status"] == "match" else "  <-- " + "; ".join(entry["problems"][:2])
        if entry.get("tags"):
            flag += f"  [{','.join(entry['tags'])}]"
        print(f"[{idx:>3}] {entry['status']:<13} {vol_txt}{flag}")

        if not args.keep:
            shutil.rmtree(case_dir, ignore_errors=True)

    hangs = [{"case": c["name"], "engine": k}
             for c in report["cases"]
             for k, e in c["engines"].items() if not e.get("ok") and e.get("timeout")]
    report["summary"] = {
        "total": len(indices),
        **counts,
        "hangs": hangs,
        "problem_kinds": kind_hist,
        "divergence_tags": tag_hist,
    }
    report_path = FUZZ_DIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nsummary")
    print(f"  {'status':<14} count")
    for k in ("match", "divergence", "engine-error", "degenerate"):
        print(f"  {k:<14} {counts[k]:>5}")
    if kind_hist:
        print("  problem kinds:")
        for k, v in sorted(kind_hist.items()):
            print(f"    {k:<24} {v}")
    if tag_hist:
        print("  divergence tags:")
        for k, v in sorted(tag_hist.items()):
            print(f"    {k:<24} {v}")
    if hangs:
        print("  hangs (engine timed out):")
        for h in hangs:
            print(f"    {h['case']} [{h['engine']}]")
    print(f"\nreport: {report_path}")
    findings = counts["divergence"] + counts["engine-error"]
    print(f"result: {findings} finding(s)" + ("" if findings else " -- kernels agree on this batch"))
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
