from smlibpy import Circle, Plane, extrude

result = extrude(Circle(10).on(Plane.XY) - Circle(5).on(Plane.XY), 10, taper=5)
