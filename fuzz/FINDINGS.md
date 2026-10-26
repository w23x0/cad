# fuzz/FINDINGS — 跨内核平价模糊测试发现

定位：随机 CSG 程序在 build123d(OCCT) 与 smlibpy(SMLib) 上的**平价**比较——不与手算真值比（那是 bench 的活）。
但下文个别发现做了独立真值仲裁（解析公式），已单独注明。

批次：seed `20261027`，30 cases，tol `1e-6`，单内核超时 30s。
**结果：21 match / 6 divergence / 3 engine-error / 0 degenerate**，37 s 跑完；
单次 run 最长 b123d 1.28 s、smlibpy 0.21 s，**无挂起**（hang 清单为空）。
确定性：同 seed 双跑 report.json 逐字节一致（仅 runtime_s 不同）。

数值底噪（run 前校准）：单基元体积两内核一致到 ~1e-9 rel；一般布尔链 1e-8..1e-7 rel；
OCCT bbox 带 ~1e-7 的 gap。tol=1e-6 因此选得合适：batch 里 21 个 match 都是真一致。

---

## 与已知问题 F-1 的归类关系（重要）

FINDINGS.md **F-1**（smlibpy 重叠实体布尔不可靠）给出安全路径：**穿透式切割、面接触融合、
不相交融合**。按此把本批 divergence 逐案归到"onset 操作"上：

| case | 现象 | onset 操作 | op 类别 | 归属 |
|---|---|---|---|---|
| 01 | solids 4≠3 | `p0+p1` 并(1.4e-6 噪声) → `-p2` 穿透切割相切 | 并=非穿透；**切割=穿透(安全路径)** | **FZ-5 安全路径新分歧** |
| 06 | bbox Y/Z 大偏差 | `-p2` 球上非穿透切孔 | 非穿透切割（F-1 辖区） | **FZ-2 build123d 侧**（解析仲裁） |
| 15 | 丢 6.33mm³ cell | `pre+p4` 非穿透重叠并 | 非穿透重叠并 | F-1 家族，**新模式**（FZ-4） |
| 19 | vol 4.5e-6 | `+p3` 球球并 | 非穿透重叠并 | F-1 家族（FZ-6） |
| 21 | vol 5.7e-3 + valid≠ | `p0-p1` 端面切球冠 | 非穿透切割（F-1 辖区） | **FZ-3 build123d 侧**（解析仲裁） |
| 24 | vol 2.9e-6 + faces 14≠16 | `-p1` 锥切 | 非穿透切割 | F-1 家族（FZ-6） |

**占比**：6 例分歧中 3 例（15/19/24）落在 F-1 家族（SMLib 侧异常，非穿透重叠并/切）——按约标注，不深挖；
**2 例（06/21）是 F-1 辖区操作上 build123d 自身的错误**（解析真值仲裁，增量价值所在）；
**1 例（01）是安全路径（穿透切割）上的新分歧**（相切退化语义差）。
3 例 engine-error 全是 b123d 对 `Cone(r,r,h)` 的构造域拒绝（FZ-1）。

---

## 发现明细

### FZ-1 build123d：`Cone(r1, r2, h)` 在 r1==r2 时直接抛异常；smlibpy 归一化为圆柱

- **cases** 11（`Cone(10,10,20)`）、13（`Cone(9,9,9)`）、27（`Cone(5,5,22)`）— engine-error，b123d 侧。
- b123d：`Standard_DomainError: cone with two identic radii`（OCCT 构造域拒绝）。
- smlibpy：`Cone(10,10,20)` 体积 = 6283.185307 = π·10²·20（圆柱），valid=True，3 面（其文档明示
  "Equal radii give a cylinder"）。
- 归类：**API 域语义差**。随机参数下 r1==r2 概率 ~1/10，直接吃掉约 10% 的 cone case。
- 复现：`fuzz.py --only 11 --keep`，或直接在两解释器里跑 `Cone(10, 10, 20)`。

### FZ-2 build123d/OCCT：`bounding_box()` 对带内孔的裁剪曲面**不紧**（`AddOptimal` 同样不紧）

- **case** 06，divergence（bbox Y 差 0.0494 = 4.9 万倍 tol；Z 差 2.93）。
- 最小复现（2 基元，canonical）：

  ```python
  result = Sphere(12) - Pos(-2.35, 8.32, 0) * Cylinder(5, 12)
  ```

  b123d bbox Y = 24.0；smlibpy = 23.950589067。体积一致到 4.6e-7 rel → **几何相同，是 bbox 度量语义差**。
- 仲裁（三重）：① 球的 y=0.2 极点到孔轴距离 4.37 < 5，极点已被切掉，真最大 y 在孔刃上 ≈0.1506
  （= smlibpy 值）；② OCCT 侧 `BRepBndLib.AddOptimal` 同样报 24.0 —— 对**内环（inner wire）不感知**，
  只按曲面片 UV 包围；③ 网格化 bbox ≈23.94（顶点欠采样，与解析一致）。
- 更戏剧性的原始形态：case 06 第 3 步后 b123d 的 Z 范围 26.93 **大于切割前的 24.0**——减去一块材料，
  bbox 反而变大。
- 归类：**build123d 侧**（b 类，度量层）。后果：凡依赖 OCCT bbox 做"真值"或做相减包围的工具都会
  被多报污染；bench 侧 bbox 期望值若来自 OCCT 需要警惕。

### FZ-3 build123d/OCCT：圆柱**平端面**切球冠的 cut 产出零体积无效壳（布尔实锤 bug）

- **case** 21，divergence（vol rel 5.7e-3 + valid False≠True）。
- 最小复现（2 基元，canonical）：

  ```python
  result = Sphere(6) - Pos(-1.86, 0, -2.73) * Rot(0, 90, 0) * Cylinder(9, 13)
  ```

- 解析真值：圆柱半径 9、轴距 2.73，柱壁距球心最远 8.73 < 9 —— **柱壁与球完全不相交**，只有
  x=+4.64 的平端面切下球冠 h=1.36：V = π·h²·(3R−h)/3 = 32.2299 mm³。
- smlibpy：**32.229901 ✓**，valid=True，3 面（球冠面+平面+正确封口）。OCCT：**vol = -0.0，
  valid=False，2 面，1 "solid"** —— 整个球冠蒸发，留下零体积无效壳。
- 这是一个完全普通的配置（不是刀刃/相切情形），case 21 的完整链里这个坏壳让 b123d 全局 valid=False。
- 归类：**build123d 侧**（b 类，几何层，增量价值核心）。op 落在非穿透切割（F-1 辖区），但错的是
  OCCT——与 F-1（SMLib 侧）方向相反。

### FZ-4 smlibpy：多 cell 融合并时**静默丢掉切割产生的曲面 cell**（F-1 家族新子模式）

- **case** 15，divergence（vol rel 1.8e-3 + solids 3≠2）。
- 精确复现（case 15 参数）：

  ```python
  p0 = Pos(-19.69, 14.18, 35.88) * Rot(0, 0, 90) * Box(11, 11, 18)
  p1 = Pos(-33.15, 11.2, 36.83) * Rot(0, 180, 0) * Cylinder(3, 15)
  p2 = Pos(-20.0, 11.7, 22.52) * Rot(0, 0, 90) * Cone(3, 5, 19)
  p3 = Pos(-32.12, 13.23, 34.66) * Cone(4, 9, 11)
  p4 = Pos(-17.7, 16.43, 43.0) * Rot(0, 270, 0) * Box(14, 9, 10)
  result = p0 + p1 + p2 - p3 + p4
  ```

- `pre = p0+p1+p2-p3` 在两内核都是 3 cells（2807.45 / 117.90 / **6.327**）。`+p4`（box 只与大 cell
  融合）之后：OCCT 3 cells、3606.023；**smlibpy 2 cells、3599.696 —— 6.327 mm³ 的第三 cell 蒸发**，
  且幸存 cell 的 bbox 被污染（x 延伸到被丢 cell 的 −36.15）。
- 排除实验：① 整体缩放 2×/0.5×/0.25×（sliver 50.6/6.33/0.79/0.099 mm³）**全部丢** → 不是尺寸阈值；
  ② 工具全不相交时 4 cells 全保留；③ 平面 slot 双 cell、35 mm³ 球切 sliver 均保留 →
  需要"被切出的**曲面** cell"与"发生实际融合"同时成立。
- 归类：**F-1 家族**（非穿透重叠并辖区）的**新子模式**——不是"返回本尊/算一半"，而是
  "融合时丢掉无关的第三者 cell"。按约标注，待上游一起修。

### FZ-5 相切退化语义差：OCCT 静默分裂 vs SMLib 抛 ModelingError（安全路径上的新分歧）

- **case** 01，divergence（solids 4≠3，体积一致 3.3e-7 rel，bbox 一致 1e-7）。
- canonical 复现（切柱面与盒 ±x 面精确相切）：

  ```python
  result = Box(20, 20, 20) - Rot(90, 0, 0) * Cylinder(10, 40)
  ```

  b123d：**无异常**，返回 4 个角块 lumps，valid=True；smlibpy：**ModelingError**
  （"operands may touch only along an edge, at a point or tangentially"）。
  对照组 r=10.5（不相切）：两内核 1e-15 一致 —— 分歧精确锁定在相切退化。
- case 01 的随机参数撞上近相切：穿透切割（**安全路径**）后，上下材料在切点相连——
  OCCT 记 2 个 solids，smlibpy 记 1 个（切点相连算一个 solid），于是 4≠3。
- 归类：**退化接触语义差**；两边都"有理"，但对下游（solids 计数、装配枚举）是实质差异。
  这是本批唯一落在安全路径上的 divergence —— F-1 规避手册覆盖不到它。

### FZ-6 小体积分歧：二次曲面交线的近似/容差差（F-1 家族，按约不深挖）

- **cases** 19（vol rel 4.5e-6，Δ0.0102 mm³）、24（vol rel 2.9e-6，Δ0.0225 mm³，且 **faces 14≠16**）。
- onset：19 = `+p3` 球球并；24 = `-p1` 锥切（step1 即 1.09e-6）与 `-p5` 锥切（拓扑也分裂）。
- smlibpy 自报积分噪声 ~1e-7 rel，观测差是它的 30-45 倍 → 是**真实的微小几何差**
  （交线位置差 μ 级），非积分噪声。OCCT 对二次曲面交线走近似管道，SMLib 走 NURBS 精确表示。
- 归类：**F-1 家族**（非穿透重叠并/切辖区）——小体积版本。faces 计数按设计不比较，
  但已记录在 report.json 里（case 24 的 14 vs 16 值得上游看）。

### FZ-7 空结果语义差（最小化中顺带发现，不占 batch 指标）

- `Sphere(6) - Pos(0, 0, -2.73) * Rot(0, 90, 0) * Cylinder(9, 20)`（工具全包基体）：
  b123d → 0 solids，**valid=True**，bbox [0,0,0]；smlibpy → 0 solids，**valid=False**，
  **bbox = ±2e20 哨兵值**。
- fuzzer 把双空判为 degenerate 跳过比较，所以此项不进 batch 指标；但任何消费 smlibpy 空体
  bbox 的下游代码都会被 ±2e20 毒害，valid 语义也相反。记录备查。

---

## hang / crash 清单

无。60 次 kernel run 全部在 1.3 s 内返回（超时阈值 30 s），report.json `summary.hangs` 为空。
b123d 的 3 次 engine-error 是确定性构造域异常（FZ-1），非挂起非崩溃。

## 复现命令

```bash
# 全批（默认 seed 20261027, 30 cases, tol 1e-6）
/home/w23x/CAD/envs/cad/bin/python fuzz/fuzz.py

# 单 case 重跑并保留模型（目录 fuzz/cases/seed20261027_caseNNN/）
/home/w23x/CAD/envs/cad/bin/python fuzz/fuzz.py --only 6 --keep
/home/w23x/CAD/envs/cad/bin/python fuzz/fuzz.py --only 15 --keep

# 手改参数复现：编辑 cases/ 里的 model_b123d.py（两内核共用同一份源码，仅 import 行不同）
# 逐内核跑 measure.py 即可对照；或用 --keep 后的模型直接喂 verify/measure.py。
```

## 批次附录（2026-10-27 补跑）

| 批次 | cases | 一致 | 分歧 | 引擎报错 | 备注 |
|---|---|---|---|---|---|
| seed 20261027（基准） | 30 | 21 | 6 | 3 | 详见上文逐条归因 |
| seed 1 | 40 | — | 7(体积)+3(bbox/solids) | 6 | 无新类型 |
| seed 2 | 40 | 25 | 9 | 6 | 无新类型 |

**本底漂移结论**：任意重叠布尔 CSG 上，两内核体积差稳定落在 1e-6 ~ 2e-5 相对带内
（方向不定）。这是 F-1 重叠处理不精确的本底表现。含义：
- bench 的 1e-6 契约只在**策展安全路径**（穿透切割/接触融合/不相交融合/图元）上可达，
  全部 10 件均在此带内零漂移（逐位一致）。
- 对任意 CSG，跨内核校验容差应设 ~5e-5 相对值；`fuzz.py --tol 5e-5` 可按此跑。
- `Cone(r, r, h)` 生成器模式每批稳定产出 ~6 个 b123d engine-error（smlibpy 归一化
  为圆柱）——生成器侧已知，保留作为语义差记录。

report.json 当前为 seed 20261027 基准批（复现：`fuzz.py`，无参数）。

**长批复跑（同日）**：seeds 3–7 × 50 = 250 cases → 161 一致 / 42 分歧 / 47 引擎报错。
分歧全部落在已确立类型（体积漂移 1.5e-6 ~ 3.9e-5 的 F-1 带、bbox 的 F-5 家族、
engine-error 的 Cone(r,r) 退化），无 >1e-3 的离群值，**无新 bug 类型**。

**扫描批（seeds 8–12 × 50 = 250 cases）**：无新类型；seed 12 出现首个 smlibpy
engine-error（报告被基准恢复覆盖，未留档——修复显示 bug 后未来批次会保留）。
顺带修复 fuzz.py 显示路径的 None 格式化崩溃（smlibpy 引擎报错时）。
