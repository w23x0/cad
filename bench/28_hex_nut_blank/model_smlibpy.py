from smlibpy import Cylinder, Pos, RegularPolygon

# inscribed=True -> radius is the apothem (across-flats 24 = 2*12).
# The tool must pierce the 0..10 prism: centered Cylinder(6, 12) spans -6..6 and only
# half-cuts, hence moved(Pos(0, 0, 5)) -> spans -1..11.
result = RegularPolygon(12, 6, inscribed=True).extrude(10) - Cylinder(6, 12).moved(Pos(0, 0, 5))
