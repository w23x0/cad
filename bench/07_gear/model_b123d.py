import math

from build123d import CenterArc, Cylinder, Face, Line, Rot, Wire, extrude

N, R_ROOT, R_TIP, H, R_BORE = 12, 20.0, 26.0, 10.0, 6.0
T_ROOT, T_TIP = math.radians(10), math.radians(6)
R_EXT = 18.0  # tooth blank reaches into the root disk -> transversal overlap fuse


def flank_end(r):
    """Straight flank through (R_ROOT, T_ROOT) and (R_TIP, T_TIP), cut with circle radius r."""
    p1 = (R_ROOT * math.cos(T_ROOT), R_ROOT * math.sin(T_ROOT))
    p2 = (R_TIP * math.cos(T_TIP), R_TIP * math.sin(T_TIP))
    d = (p2[0] - p1[0], p2[1] - p1[1])
    dd = d[0] * d[0] + d[1] * d[1]
    b = p1[0] * d[0] + p1[1] * d[1]
    c = p1[0] ** 2 + p1[1] ** 2 - r * r
    t = (-b + math.sqrt(b * b - dd * c)) / dd  # root of interest: just inside R_ROOT
    return (p1[0] + t * d[0], p1[1] + t * d[1])


q = flank_end(R_EXT)
dq = math.degrees(math.atan2(q[1], q[0]))
tip = (R_TIP * math.cos(T_TIP), R_TIP * math.sin(T_TIP))

wire = Wire(
    [
        CenterArc((0, 0), R_EXT, -dq, 2 * dq).edge(),
        Line(q, tip),
        CenterArc((0, 0), R_TIP, math.degrees(T_TIP), -2 * math.degrees(T_TIP)).edge(),
        Line((tip[0], -tip[1]), (q[0], -q[1])),
    ]
)
tooth = extrude(Face(wire), H / 2, both=True)

result = Cylinder(R_ROOT, H)
for i in range(N):
    result += Rot(0, 0, i * 360 / N) * tooth
result -= Cylinder(R_BORE, H + 2)
