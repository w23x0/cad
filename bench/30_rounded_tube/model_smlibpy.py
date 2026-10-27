from smlibpy import Slot

# Sketch-level ring (face with inner wire) extruded once: bit-exact on both kernels.
# Probe: Slot(length, width) is overall length, == b123d SlotOverall(50, 30).
result = (Slot(50, 30) - Slot(30, 10)).extrude(10)
