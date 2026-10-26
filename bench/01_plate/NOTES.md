# 01 plate

The most basic golden part: a box with four through holes and a blind pocket.
It exercises boolean cuts, pattern placement, pocket depth and the bounding box.
All kernels must return the same volume.

- Body: 80 x 60 x 10
- Holes: 4 x Ø8 through, at (±30, ±20)
- Pocket: 30 x 20, 4 mm deep from the top face (z = +5)

Expected volume = 80*60*10 - 4*π*4²*10 - 30*20*4 = 43589.3807 mm³

## 质心手算

质心：x=y=0（全对称）；穿孔沿 z 均匀不移质心；pocket 2400 位于 z∈[1,5]（质心 +3）→ z = −2400·3/V = −0.16517785。
