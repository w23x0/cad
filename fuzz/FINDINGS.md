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

---

## 批次附录（2026-10-27 第二次：算子池升级后，seeds 13–17）

**算子池变更**（对 seeds 13+ 及其后所有批次生效；历史批次的 13 以下 seed 数字不可跨池比较）：

1. **Cone(r,r) 退化消除**：生成 Cone 时 |r1−r2|/max(r1,r2) < 1e-3 即重采样半径。
   FZ-1（b123d `Standard_DomainError` vs smlibpy 归一化圆柱）已归类为 API 域语义差，
   不再让生成器重复制造该 engine-error。效果：本 300 例 **b123d engine-error = 0**
   （升级前每 30 例约 3 例）。
2. **新增 revolve 基元**（基元抽取 ~20% 权重）：XZ 平面矩形/直角梯形轮廓
   （局部 x=半径 8..20，局部 y=高度 ±8 内），绕 Axis.Z 转 {90,180,270,300}°。
   **手工探针结论（revolve）**：两内核签名相同 `revolve(profile, Axis.Z, angle)`，
   同起点（轮廓相位 +X）、同方向（绕 +Z 逆时针）——90° 探针 bbox min/max 逐位一致
   （min (0,0,2)、max (15,15,6)）；`Pos*Rot*revolve` 链两内核一致；90/180/270° 两内核
   体积皆精确到机器精度（解析 annulus 公式仲裁），300° 见 FZ-10。语义完全可比，入池。
3. **新增 split 算子**（每操作 ~18% 概率）：对累计结果做平面剖分；平面过参考基元中部
   （真实穿体），z_dir ∈ {(0,0,1),(1,0,1),(1,0,0)}，x_dir 取垂直向量，保留侧
   above/below 各半。**手工探针结论（split）**：
   - keep 映射：**smlibpy `split(part, plane, keep="above")` ≡ b123d
     `split(part, bisect_by=plane, keep=Keep.TOP)`**（above/TOP = 平面 z_dir 指向侧；
     "below" ≡ Keep.BOTTOM）。轴对齐探针（Box(20,20,20) 截 z=5：2000/6000）与 45° 平面
     （解析 2890）两内核逐位一致；平面穿并集体、多 cell（2 离散盒 → 2 solids/1000）
     亦逐位一致。**唯一源码差异**是这一行的引擎拼写（几何与保留侧来自同一份共享参数）。
   - keep="both" 不入池：smlibpy 返回 (above, below) 元组、两半融回 **1 solid**；
     b123d Keep.BOTH 返回 **2-solid Compound**（体积/bbox 一致、solids 1≠2）——
     拓扑语义不可直接比，生成器只取单侧。
4. **divergence 自动标签**：bbox 类 → `F-5-family`；体积相对差 ≤ 5e-5 且 union 链含
   AABB 重叠 → `F-1-family`；其余 → `NEW`（逐条手工最小化，见 FZ-8/9/10）。

### 批次统计（tol 1e-6，单内核超时 30s，总墙钟 ~11 min，无 hang）

| 批次 | cases | 一致 | 分歧 | 引擎报错 | 退化 | 标签 F-1/F-5/NEW |
|---|---|---|---|---|---|---|
| seed 13 | 60 | 47 | 11 | 2 | 0 | 5 / 5 / 1 |
| seed 14 | 60 | 47 | 12 | 1 | 0 | 8 / 3 / 1 |
| seed 15 | 60 | 50 | 7 | 3 | 0 | 4 / 2 / 1 |
| seed 16 | 60 | 49 | 8 | 3 | 0 | 3 / 4 / 1 |
| seed 17 | 60 | 49 | 7 | 4 | 0 | 5 / 2 / 0 |
| **合计** | **300** | **242** | **45** | **13** | **0** | **25 / 16 / 4** |

问题种类直方图（问题条数，非 case 数）：volume 32、bbox.X 8、bbox.Y 7、bbox.Z 7、
solids 4、valid 3、engine-error:smlibpy 13。确定性：seed 99 双跑 report.json
除 runtime_s 外逐字节一致。

engine-error 全部在 smlibpy 侧：12 例 = split 空侧语义差（见下），1 例（seed17 c19）
= FZ-5 相切 `ModelingError` 家族（fuse 阶段 "operands may touch only ... tangentially"）。

### split 空侧语义差（engine-error 噪声源，FZ-7 的 split 版，不占 NEW）

keep 侧无材料时：**b123d 静默返回空体（0 solids、valid=True、vol 0）**；smlibpy 抛
`ModelingError: split: nothing of the part lies above/below the plane`。本批 12/300 ≈ 4%
的 case 撞上（split 平面穿过被 subtract 掏空的参考基元区）。方向与 FZ-5 相同：
smlibpy 报错优于 b123d 静默；下游若消费 b123d 的空 split 结果会被 0 尺寸 bbox 毒害。
按 engine-error 记录，不深挖。

### FZ-8 smlibpy：并集静默丢弃无关 cell——最小触发不需要"切出的 cell"（NEW ×2：seed13 c32、seed15 c33）

最小复现（圆整参数，canonical）：

```python
A = Pos(-25, 10, -31) * Cylinder(5, 4)
B = Pos(-16, 19, -26) * Box(10, 10, 10)
tool = Pos(-13, 20, -17) * Box(12, 12, 12)
result = A + B + tool
```

- 解析/b123d：**2882.159265、2 solids**（= 1000 + 314.159 + 1728 − 160 tool∩B）。
- smlibpy：**2568.000000、1 solid** —— A 的 314.159 mm³（π·5²·4）**整段蒸发**，Δ 恰等于 A。
- 触发条件（逐因子最小化）：A 与 B 实体不相交，但 **B 的 AABB 三轴全部与 A 的 AABB 交错**
  （B 的角插进圆柱 AABB 的空角——三轴交错而实体不相交只有曲面体才可能）；tool 与 B 融合。
  对照：AABB 2 轴交错不触发；对角布置（0 轴交错）在 0.5..16 mm 全部间距不触发；
  A 为 box 时 pre 直接 1 cell 无法构成 2-cell 前提。
- **构造来历敏感**：同一几何的 A 若来自 `split(...)`（平面剖分产物）则**幸存**
  （2882.159265 正确）——同形状不同来历，结果不同。但真实 case（seed13 c32）里
  split 产物的 lump 同样被丢，说明来历只是调制因素，不是保命符。
- seed15 c33 同型：`+p3`（球）时 smlibpy 丢掉整个 `(p0−p1)` lump，Δ = 1991.093 =
  pre 中该 lump 体积的精确值；b123d 3 cells/11558.544 vs smlibpy 2 cells/9567.537。
- 归类：**F-6/FZ-4 家族**（融合丢 cell）的**新最小触发**——不再需要"被切出的曲面
  cell"，普通不相交圆柱即可。与 F-1"包含/相交分类失效"的 bbox 级误判嫌疑自洽
  （三轴 AABB 交错≈bbox 相交，内核可能据此走了错误的相交/包含分支）。分类器按约定打
  NEW（体积差 10.9%/17.2% 远超 5e-5 阈值），人工归因后归 F-6 家族。

### FZ-9 build123d/OCCT：球冠 cut 体积随球面参数化朝向（Rot）变化（NEW ×1：seed16 c16）

最小复现（canonical，纯球-平面切割，无布尔链）：

```python
s = Rot(0, 90, 0) * Sphere(6)
result = split(s, bisect_by=Plane((0, 0, 0.07), (1, 0, 0), (0, 0, 1)), keep=Keep.TOP)
```

- 解析（球冠 V = π·h²(3R−h)/3, h=5.93）= **444.472888 = smlibpy 逐位**；
  **b123d = 444.537877（+0.064990，+1.46e-4 rel）**。两内核均 1 solid / 2 faces / valid。
- Rot 扫描（同一球、同一平面）：(0,0,0) 精确、**(0,90,0) +1.46e-4、(90,0,0) −1.65e-3**、
  (0,45,0) −4e-8、(0,0,90) 与 (0,180,0) 精确。位置无关（平移到原点同样 +0.064990）；
  平面原点 xy 无关；切割深度 0..4 mm 在未旋转球上全精确。
- 归因：**build123d/OCCT 侧（几何层）**。球-平面布尔结果依赖球面的 UV 参数化朝向
  （切平面相对球面局部赤道/极点/缝合线的位置改变数值路径）；smlibpy 对所有朝向精确。
- 链路：case16 的 revolve 无关——p0 = `Pos·Rot(0,90,0)·Sphere(6)`（生成器随机 Rot），
  sphere∪sphere 体积两内核本一致（2.4e-8 rel），final split（平面过 p0 球心上方 0.07）
  后 cap 体积差 0.065 mm³；`−p2` 是 no-op（锥完全在材料外）。
- 对 bench 的威胁：凡球体经随机 Rot 再做 cut/测量体积的件，OCCT 可能带 1e-4~1e-3
  相对误差；bbox/faces/valid 均正常，纯体积错。

### FZ-10 smlibpy：300° 部分角旋转体体积近似（NEW ×1：seed14 c31，轻微）

- 角度扫描（annulus r∈[8,16]、z∈[−4,4]，解析 π·(16²−8²)·8·θ/360）：
  90/180/270° 两内核皆精确到机器精度；**300° smlibpy −4.53e-7 rel**（b123d +3.4e-16 精确）。
- case31 链路：300° revolve 基元（梯形轮廓）源头差 3.7e-7 rel（957.192312 vs 957.192667），
  后续 4 次切割把体积缩到 11.27 mm³，**相对差放大到 2.5e-6 > tol 1e-6** → divergence。
  smlibpy 同时自报 RuntimeWarning "faces ... do not meet exactly (gaps), volume
  uncertain by about 1e-5"——与观测一致的自知近似。
- 归类：smlibpy 侧近似精度（非拓扑/非语义），体量大时低于 tol；生成器保留 300°
  （体积放大效应反而是有效的灵敏度探针）。

### 结论

- 新增算子探针阶段全部可比（revolve 完全、split 单侧完全），没有"语义差太大不可比"
  而被拒收的算子；keep="both" 因拓扑不可比排除出池（见算子池变更 3）。
- 4 例 NEW 全部定因：FZ-8（smlibpy 丢 cell，F-6 家族新触发，2 例）、FZ-9（b123d 球冠
  Rot 敏感体积误差，1 例，**增量价值最高**）、FZ-10（smlibpy 300° 近似，1 例，轻微）。
- FZ-9 建议后续：bench 侧含球+cut 的件若报体积不齐，先查球面 Rot。

复现命令（本附录批次）：

```bash
/home/w23x/CAD/envs/cad/bin/python fuzz/fuzz.py --seed 13 --cases 60 --no-strict   # ... 14..17
/home/w23x/CAD/envs/cad/bin/python fuzz/fuzz.py                                    # 基准 seed 20261027 ×30
```

report.json 当前为 seed 20261027 基准批（升级后生成器首跑：25 match / 2 divergence
（均 F-1-family）/ 3 engine-error（split 空侧语义差）；Cone 退化 engine-error 已绝迹）。
