from build123d import Ellipse, extrude

# Sketch-level ring (face with inner wire) extruded once: bit-exact on both kernels.
# Do NOT switch to solid-level booleans here: on OCCT the piercing cut of the inner
# elliptical cylinder perturbs geometry (volume rel ~7.4e-7, centroid shifts ~5e-6).
result = extrude(Ellipse(15, 10) - Ellipse(10, 5), 12)
