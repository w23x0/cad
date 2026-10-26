from smlibpy import Plane, Rectangle, extrude

result = extrude(Rectangle(40, 30).on(Plane.XY), 20, taper=10)
