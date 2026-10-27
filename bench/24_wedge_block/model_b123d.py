from build123d import Rot, Wedge

# OCCT wedge: slanted face at +Y, defined by (xmin, zmin, xmax, zmax). Collapse it
# to an edge (0, 0, 40, 0) and rotate -90 deg about Z so the ramp descends along
# +X with the high wall at -X, matching the smlibpy primitive's orientation.
result = Rot(0, 0, -90) * Wedge(40, 60, 20, 0, 0, 40, 0)
