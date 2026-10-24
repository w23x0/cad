# bench — golden parts

Every subfolder is a "golden part": the same design intent implemented on two
independent kernels. Metrics must match `expected.json` **and** each other.

| Part | Exercises | Volume mm³ |
|---|---|---|
| `01_plate` | boolean cuts, 4-hole pattern, blind pocket, bbox | 43589.3807 |
| `02_l_bracket` | closed polyline → face → extrude → holes | 35978.7614 |
| `03_flange` | revolved solid, centre bore, polar pattern | 23436.2812 |

## Adding a part

1. Create `bench/NN_name/`.
2. Write `NOTES.md` with dimensions and the **hand-computed** volume.
3. Write `model_b123d.py` and `model_smlibpy.py`, both assigning `result`.
4. Run the verifier; once both kernels agree, put the hand value in `expected.json`.

`expected.json` must contain the hand calculation, never a value copied from a
run — otherwise the test only proves self-consistency.

## Why two kernels

A single kernel can be wrong in ways that still look valid. Two independent
implementations (OCCT vs SMLib) agreeing on volume, bbox, solid count and
validity makes that much less likely. A disagreement is either a kernel bug or
an ambiguous design — both worth finding before export.

This set doubles as an objective scoreboard: change a model, a prompt, or a
kernel, rerun it, and regressions show up immediately.

## Current status

3 parts, 6 implementations, all passing with relative error < 1e-6.
