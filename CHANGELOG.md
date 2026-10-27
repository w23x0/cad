# Changelog

## 2026-10-27

- bench: 22 golden parts (44 dual-kernel implementations), all passing with
  volume/bbox/centroid(/interference) contracts, max relative error < 1e-6.
- verify: centroid + interference metrics added to the contract; white-background
  technical-drawing PNGs.
- fuzz: operator pool upgraded (revolve, split; Cone-degenerate cases removed),
  auto-tagging of divergences (F-1/F-5/NEW); ~1300 cases run across seeds,
  findings FZ-8/9/10.
- FINDINGS: F-1..F-9 + FZ-8/9/10 kernel divergences documented with minimal
  repros and Monte-Carlo arbitration; upstream issue drafts prepared.
- mcp: end-to-end stdio test (37 assertions); CI workflow for the future public repo.

## 2026-10-26

- Initial public-repo-ready state: two-kernel verify harness, MCP server,
  3 seed bench parts (plate, L bracket, flange).

## 2026-10-27 (wave C)

- bench: parts 23-31 via parallel agents (chamfer rim, wedge block,
  fusion mix, eccentric void, elliptical tube, hex nut blank, silo,
  rounded tube, float ring) — 31 parts, 62 implementations, all passing.
- FINDINGS: FZ-11 (OCCT solid-level ellipse boolean imprecise);
  FZ-8 boundary refined (needs >=3-body fuse chain); kernel semantic
  notes on Wedge orientation, RegularPolygon phases, Slot equivalence.
- fuzz: long scan partially completed (seeds 31-32 before quota kill);
  new unminimized report: smlibpy ZeroDivisionError (seed32 c12).
  Canonical report restored (seed 20261027).
- Deferred by quota kill: smlibpy 0.5.0 full trial, verify --baseline.
