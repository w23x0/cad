from smlibpy import Polyline, loft, make_face

f1 = make_face(Polyline((20, 20, -8), (-20, 20, -8), (-20, -20, -8), (20, -20, -8), close=True))
f2 = make_face(Polyline((10, 15, 8), (-10, 15, 8), (-10, -15, 8), (10, -15, 8), close=True))
result = loft([f1, f2], ruled=True)
