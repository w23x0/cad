from smlibpy import Plane, Sphere

result = Sphere(15).split(Plane.XY.offset(5), keep="below")
