## [0.3.3 & 0.5.0] Fusing a multi-cell part with a non-piercing tool silently drops a cell

Related to the overlapping-boolean containment issue but a distinct failure mode:
no exception, `is_valid()` True, volume quietly loses a whole lump.

### Repro sketch

A part with 3 disjoint cells fused with a tool that overlaps (but does not pierce)
one region: the third cell (6.327 mm³ in the minimized case) disappears from the
result. Reproduces at 2×, 0.5× and 0.25× uniform scale; with a fully disjoint
tool all cells survive. Deterministic seeded repro available (fuzzer case 15,
minimized to 2 primitives; full harness on request).

Expected: fuse keeps all cells, or raises.
