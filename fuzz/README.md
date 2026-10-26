# fuzz — 跨内核平价模糊测试器

用随机 CSG 程序找 build123d(OCCT) 与 smlibpy(SMLib) 的几何分歧。这是**平价测试器**：
两内核跑**同一份**随机设计，只互相比——不与手算真值比（解析真值归 `../bench` + `../verify`）。
发现的分歧就是内核 bug 或语义差异，逐条归因见 [FINDINGS.md](FINDINGS.md)。

## 原理

每个 case 由共享随机参数生成一个 CSG 设计：4-8 个基元
（Box(w,d,h) / Cylinder(r,h) / Sphere(r) / Cone(r1,r2,h) / 部分角旋转体 revolve），
3-6 个 union/subtract/split 操作；平移采样于 [-40,40] 并钳制进 [-50,50]³，旋转角取自 {0,45,...,315}°
（单轴）。同一份参数渲染成 `model_b123d.py` 与 `model_smlibpy.py`——**两者除 import 行外逐字节相同**
（两内核共享 build123d 式代数模式：`Pos * Rot * Shape`、`+ - &`），唯一例外是 split 调行的
引擎拼写（几何与保留侧来自同一份共享参数，见下），所以任何指标差异都是内核差异。

### 2026-10 算子池升级（seeds 13+ 生效）

- **Cone(r,r) 退化消除**：|r1−r2|/max(r1,r2) < 1e-3 时重采样半径（FZ-1 的 b123d
  `Standard_DomainError` 已归类为 API 域语义差，不再重复测量）。
- **revolve 基元**（约 20% 的基元）：XZ 平面上的矩形/直角梯形轮廓
  （局部 x = 半径 8..20，局部 y = 高度 ±8 内），绕 Axis.Z 转 {90,180,270,300}°。
  两内核语义经手工探针确认一致：同起点（轮廓相位 +X）、同方向（绕 +Z 逆时针）、
  同签名 `revolve(profile, Axis.Z, angle)`（探针 r1：90° bbox min/max 逐位一致；
  解析 Pappus 仲裁 90/270° 两内核精确、300° smlibpy 带 ~5e-7 rel 噪声）。
- **split 算子**（每操作 ~18% 概率）：对累计结果做平面剖分，平面过参考基元中部
  （真实切到材料），法向取 {(0,0,1),(1,0,1),(1,0,0)}，保留侧 above/below 各半。
  keep 语义对应（探针 s1/s2，含 45° 平面解析值 2890 逐位一致）：
  **smlibpy `split(part, plane, keep="above")` ≡ b123d `split(part, bisect_by=plane, keep=Keep.TOP)`**
  （"above"/TOP = 平面 z_dir 指向的一侧；"below" ≡ Keep.BOTTOM）——模型里仅这一行的
  引擎拼写不同。keep="both" 不进池：smlibpy 返回元组、两半融回 1 solid，
  b123d Keep.BOTH 返回 2-solid Compound（探针 s5），拓扑语义不可直接比。
- **divergence 自动标签**：bbox 类 → `F-5-family`；体积相对差 ≤ 5e-5 且 union 链含
  AABB 重叠 → `F-1-family`；其余 → `NEW`（逐条手工最小化，见 FINDINGS.md）。

指标经 `../verify/measure.py` 协议采集（volume_mm3、bbox_mm、solids、valid；faces/edges 记录但不比较——
拓扑计数在两内核间合法地不同）。比较器：体积相对差 > tol、bbox 各轴绝对差 > tol、solids 或 valid
不等 → divergence；某内核报错/超时（30s）→ engine-error；双空（体积 <1e-3 mm³）→ degenerate 跳过。
split 的空侧语义差（b123d 静默空体 vs smlibpy `ModelingError`，探针 case seed99/06）按 engine-error 记录。

## 用法

```bash
# 默认：seed 20261027, 30 cases, tol 1e-6, 单内核超时 30s
/home/w23x/CAD/envs/cad/bin/python fuzz/fuzz.py

# 常用变体
fuzz.py --seed 42 --cases 10 --tol 1e-7     # 更严的容差
fuzz.py --only 6,15 --keep                  # 只跑指定 case 并保留模型目录（复现/手改用）
fuzz.py --no-strict                          # 有发现也退出 0（默认有 divergence/error 退出 1）
```

解释器解析顺序同 verify.py：环境变量 `CAD_B123D_PYTHON` / `CAD_SMLIBPY_PYTHON`，
否则 `../envs/cad/bin/python` 与 `../smlibpy/venv/bin/python`。

## 输出

- 进度行：每 case 一行 `[NNN] status vol A/B`，分歧带前两条 problem。
- 结束汇总：match/divergence/engine-error/degenerate 计数、problem 类型直方图、hang 清单。
- `report.json`：机器可读。每 case 的 seed、完整参数（可重建模型）、两内核指标或错误尾、
  分类与 problems；`summary.hangs` 单列超时（挂起单独归类，不与普通 error 混淆）。
- 退出码：全部一致 → 0；有 divergence/engine-error → 1（`--no-strict` 关掉）。

复现一个发现：`fuzz.py --only N --keep` 重新生成该 case，模型在
`fuzz/cases/seedNNN_caseNNN/model_{b123d,smlibpy}.py`；可直接手改参数后用
`../verify/measure.py` 逐内核对照。最小化案例与归因都在 FINDINGS.md。

## 已知局限

- **F-1 噪声**：smlibpy 的非穿透重叠并/切本底不可靠（见 `../FINDINGS.md` F-1），落在该辖区的
  divergence 要先按 F-1 家族归类再谈增量；本批 6 例分歧中 3 例属此（FINDINGS.md 有占比表）。
- **bbox 语义差是"真分歧"但非几何分歧**：OCCT bbox 对带内孔的裁剪曲面不紧（FZ-2），体积一致而
  bbox 不一致时先想这一条。
- 生成器刻意停留在"安全区"：只用基元和直纹布尔，无螺旋扫掠/渐开线样条/loft/sweep/fillet；
  旋转单轴、角度 45° 网格。若连安全区都出分歧（本批 FZ-2/3/5），那正是要抓的。
- 平移钳制：为保证基元整体在 [-50,50]³，采样值会被钳制，大基元的平移范围实际小于 ±40。
- 空结果（双内核体积 <1e-3 mm³）判 degenerate 跳过——两内核对空体的 valid/bbox 语义本就相反
  （FZ-7），比较无意义。
- faces/edges 只记录不比较：拓扑计数差异是内核的合法自由度（但 case 24 的 14 vs 16 值得看）。
- 单 case 两内核各跑一次 `measure.py` 子进程，含解释器启动；本批 30 cases 约 37 s，
  smlibpy 单次最长 0.21 s、b123d 1.28 s——30s 超时相当宽裕，真正的挂起会被干净地记入 hangs。
- `fuzz/cases/` 默认跑完即删（`--keep` 保留），gitignore 掉；report.json / FINDINGS.md / fuzz.py 入库。
