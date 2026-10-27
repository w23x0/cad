from build123d import Sphere, Torus

# Disjoint 2-solid fuse: torus inner edge rho 12 > sphere r10 (2 mm clearance).
# Probe: concentric nested-AABB disjoint fuse does NOT trigger the smlibpy FZ-8
# cell drop (that needs a >=3-body fusion chain); both kernels keep 2 solids.
result = Sphere(10) + Torus(16, 4)
