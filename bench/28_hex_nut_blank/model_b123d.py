from build123d import Cylinder, Pos, RegularPolygon, extrude

# major_radius=False -> radius is the apothem (across-flats 24 = 2*12).
# Both kernels put the first corner on +X at rotation=0, so no phase alignment needed.
# The tool must pierce the 0..10 prism: centered Cylinder(6, 12) spans -6..6 and only
# half-cuts, hence Pos(0, 0, 5) -> spans -1..11.
result = extrude(RegularPolygon(12, 6, major_radius=False), 10) - Pos(0, 0, 5) * Cylinder(6, 12)
