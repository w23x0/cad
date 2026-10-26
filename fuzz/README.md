# fuzz — 跨内核平价模糊测试器

用随机 CSG 程序找 build123d(OCCT) 与 smlibpy(SMLib) 的几何分歧。这是**平价测试器**：
两内核跑**同一份**随机设计，只互相比——不与手算真值比（解析真值归 `../bench` + `../verify`）。
发现的分歧就是内核 bug 或语义差异，逐条归因见 [FINDINGS.md](FINDINGS.md)。

## 原理

每个 case 由共享随机参数生成一个 CSG 设计：4-7 个基元
（Box(w,d,h) / Cylinder(r,h) / Sphere(r) / Cone(r1,r2,h)），
3-6 个 union/subtract 操作；平移采样于 [-40,40] 并钳制进 [-50,50]³，旋转角取自 {0,45,...,315}°
（单轴）。同一份参数渲染成 `model_b123d.py` 与 `model_smlibpy.py`——**两者除 import 行外逐字节相同**
（两内核共享 build123d 式代数模式：`Pos * Rot * Shape`、`+ - &`），所以任何指标差异都是内核差异。

指标经 `../verify/measure.py` 协议采集（volume_mm3、bbox_mm、solids、valid；faces/edges 记录但不比较——
拓扑计数在两内核间合法地不同）。比较器：体积相对差 > tol、bbox 各轴绝对差 > tol、solids 或 valid
不等 → divergence；某内核报错/超时（30s）→ engine-error；双空（体积 <1e-3 mm³）→ degenerate 跳过。

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
