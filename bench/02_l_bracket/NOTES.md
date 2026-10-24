# 02 L bracket

The smallest sketch-to-solid flow: closed polyline → face → extrude, then holes
through the extrusion. It checks that both kernels treat sketches, extrusion
and Z-axis holes identically.

- L profile: 60 x 10 horizontal leg, 10 x 50 vertical leg, extruded 40
- Holes: 2 x Ø8 through, centred at (30, 5) and (5, 30), along Z
- Profile area: 1000 mm²

Expected volume = 1000*40 - 2*π*4²*40 = 35978.7614 mm³
