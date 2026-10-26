from smlibpy import CenterArc, Circle, sweep

arc = CenterArc((0, 0), 20, 0, 270)
# F-9: smlibpy auto-places the profile at the path start and orients it.
result = sweep(Circle(5), arc)
