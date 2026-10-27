# 24_wedge_block — 楔形块（Wedge 基元）

## 设计意图

60×40×20 尖顶楔块（直角三棱柱）：高墙在 −X，斜面沿 +X 降到 z=−10，宽 40 沿 Y，
居中。特征：两内核的 **Wedge 基元**对照 + 多面体精确真值（无曲面、无积分误差）。

## Wedge 探针结论（先探后建）

- **smlibpy** `Wedge(length, width, height, top_length=0, *, align=CENTER)`：
  截面在 XZ，length 沿 X（斜面方向，高端在 −X），width 沿 Y，height 沿 Z；
  top_length>0 给平顶（梯形截面）。`Wedge(60,40,20)`：bbox (−30,−20,−10)..(30,20,10)，
  V = 24000.000000000007，5 面，high wall 在 −X。
- **build123d** `Wedge(xsize, ysize, zsize, xmin, zmin, xmax, zmax, rotation, align=CENTER×3, mode)`
  （OCCT 语义）：斜面在 y=+ysize 侧，用 (xmin..xmax)×(zmin..zmax) 定义该斜面；
  退化为边 (0,0,40,0) 即尖顶楔，**斜面沿 Y 方向**（与 smlibpy 差 90°）。
  `Wedge(40,60,20,0,0,40,0)`：V = 24000，5 面，high wall 在 −Y。
- **判定（按 bbox+体积对照标准）**：两基元对"60×40×20 尖顶楔"给出**同 bbox、同
  体积、同拓扑（5 面 9 边 6 顶点）**——尺寸语义一致，仅朝向差一个绕 Z 的 90°、
  签名形式不同（OCCT 用塌缩面矩形定义斜面 vs smlibpy 用 top_length）。
  → 采用两内核 Wedge 基元构造同一 canonical 朝向（高墙 −X、沿 +X 下降）：
  b123d 侧 `Rot(0,0,-90) * Wedge(40,60,20,0,0,40,0)`，探针确认与 smlibpy
  `Wedge(60,40,20)` **顶点逐点相同**（平面体旋转精确，无 FZ-9 风险）。
  备选等价构造（Polyline 三角形 + extrude，02 同款）无需启用，真值不变。

## 体积手算

直角三角形截面（XZ：底 60、高 20）沿 Y 拉伸 40：

V = ½ · 60 · 20 · 40 = **24 000** mm³

## 质心手算

三角形顶点 (x,z) = (−30,−10)、(30,−10)、(−30,10)：x̄ = −10，z̄ = −10/3；
沿 Y 对称 → ȳ = 0。质心 = **(−10, 0, −10/3)** = (−10, 0, −3.3333333333333335)。

## bbox / 拓扑

bbox = [60, 40, 20]（b123d 经旋转后尺寸带 ≤1.8e-14 的浮点噪声，远小于 1e-6）；
solids = 1，faces = 5（底、高墙、斜面、两个三角端面），edges = 9，vertices = 6
（Euler V−E+F = 2 自洽）。

## 容差

默认 1e-6 不放宽。两内核体积逐位 24000（smlibpy 带 7e-15 浮点尾数），质心
偏差 ≤1.4e-14，全部远低于契约。
