# 02 L bracket

The smallest sketch-to-solid flow: closed polyline → face → extrude, then holes
through the extrusion. It checks that both kernels treat sketches, extrusion
and Z-axis holes identically.

- L profile: 60 x 10 horizontal leg, 10 x 50 vertical leg, extruded 40
- Holes: 2 x Ø8 through, centred at (30, 5) and (5, 30), along Z
- Profile area: 1000 mm²

Expected volume = 1000*40 - 2*π*4²*40 = 35978.7614 mm³

## 质心手算

质心：轮廓（角在原点）COM=(20,15)；两孔各去 16π，位于 (30,5)、(5,30) → x=(1000·20−16π·35)/(1000−32π)=20.279418，y=(1000·15−16π·35)/(1000−32π)=14.720582；挤出均匀 z=20。
