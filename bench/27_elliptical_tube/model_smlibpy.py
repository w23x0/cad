from smlibpy import Ellipse

# Sketch-level ring (face with inner wire) extruded once: bit-exact on both kernels.
result = (Ellipse(15, 10) - Ellipse(10, 5)).extrude(12)
