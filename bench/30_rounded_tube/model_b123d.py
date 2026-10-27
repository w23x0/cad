from build123d import SlotOverall, extrude

# Sketch-level ring (face with inner wire) extruded once: bit-exact on both kernels.
# Do NOT switch to solid-level booleans (27_elliptical_tube finding: OCCT perturbs).
# Probe: SlotOverall(overall_length, end_diameter) == smlibpy Slot(length, width).
result = extrude(SlotOverall(50, 30) - SlotOverall(30, 10), 10)
