from smlibpy import Axis, Plane, Polygon, revolve

sec = Plane.XZ * Polygon((10, -5), (20, -5), (20, 5), (10, 5), align=None)
result = revolve(sec, Axis.Z, 300)
