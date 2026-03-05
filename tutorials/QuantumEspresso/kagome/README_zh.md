# Kagome（2×2×1）在 BandUPpy 中做能带反折叠：从仓库实测流程出发的新手教程

> 本教程不是“凭经验写法”，而是按本仓库已有文档与示例脚本整理：
> - `README.md`（总览）
> - `docs/USAGE.md`（标准 API 步骤）
> - `tutorials/QuantumEspresso/run_banduppy_qe.py`（QE 官方示例流程）
> - 以及你提供的 `tutorials/QuantumEspresso/kagome/scf.in`、`band.in`

---

## 1. 先统一概念：你的输入、BandUPpy 的职责、QE 的职责

你现在已经有：

- `scf.in`：超胞 SCF 输入；
- `band.in`：超胞 band 路径输入（`K_POINTS {crystal_b}`）。

### QE 做什么？
QE 负责产生可读的波函数数据（`<prefix>.save`）。

### BandUPpy 做什么？
BandUPpy 读取 QE 的波函数后，执行 `Unfold()`，把超胞能带权重投影回原胞 BZ。

### 为什么会出现“原胞路径→超胞路径”这一步？
因为 `docs/USAGE.md` 的标准教学流程里，确实包含：
1) 先给原胞路径；
2) 用 `generate_SC_Kpts_from_pc_k_path()` 生成等价超胞 k 路径；
3) 再计算和 unfold。

但这一步**不是唯一入口**：
- 如果你已经手工准备好超胞 `K_POINTS`（你现在就是这种情况），可以直接使用，不必强制生成。

---

## 2. 本仓库确认过的标准步骤（QE 路线）

按 `tutorials/QuantumEspresso/run_banduppy_qe.py` 和 `docs/USAGE.md`，完整流程是：

1. （可选）生成超胞路径 k 点文件。  
2. 跑 QE `scf`。  
3. 跑 QE `bands`（本教程的 `band.in` 即 `calculation='bands'`）。  
4. `banduppy.BandStructure(code="espresso", prefix=...)` 读取波函数。  
5. `Unfolding.Unfold(...)` 做反折叠。  
6. `Plotting.plot_ebs(...)` 画图并保存。

这就是你要遵循的主线。

### 补充：为什么有时写 nscf，有时写 bands？
在 QE 里两者都属于“非自洽”阶段（都依赖已收敛电荷密度），但用途不同：
- `nscf`：常用于均匀网格积分（DOS、后处理等）；
- `bands`：常用于沿指定高对称路径输出能带。

你当前 Kagome 的 `band.in` 明确写的是 `calculation = 'bands'`，所以本教程应写 **SCF + bands**，不是 SCF + nscf。

---

## 2.1 关于“直接用超胞 k 路径”的来源与边界（重要）

你问得非常专业。这里明确说明：

- **本仓库文档 `docs/USAGE.md` 的主流程**是“原胞路径 → `generate_SC_Kpts_from_pc_k_path()` → unfold”；
- 我之前加入的“直接复用 `band.in` 里的超胞 `K_POINTS`”是**便捷工程模式**，目的是减少你重复改输入；
- 这种便捷模式可用于跑通 QE+读取+unfold，但在“原胞高对称路径标签严格对应”这件事上，不如主流程严格。

因此建议：

1. 若你追求可复现实验/论文图，优先用主流程（`USE_EXISTING_SC_KPOINTS=False`）；
2. 若你先想快速验证链路是否可跑通，可用便捷模式（`USE_EXISTING_SC_KPOINTS=True`）。

---

## 3. 你的 Kagome 目录对应两种可运行模式

脚本：`run_banduppy_qe_kagome.py`

### 模式 A（便捷模式）
**直接使用你提供的超胞 k 点**（来自 `band.in`）。

- 配置：`USE_EXISTING_SC_KPOINTS = True`。
- 适合：快速跑通流程、复用既有 QE 输入。
- 注意：该模式下高对称点标签不保证严格对应原胞路径。

### 模式 B（推荐主流程）
**从原胞路径自动生成超胞路径**。

- 配置：`USE_EXISTING_SC_KPOINTS = False`。
- 脚本会使用：
  - `SUPER_CELL`
  - `PC_BZ_PATH`
  - `NPOINTS_PER_SEG`
- 并生成 `KPOINTS_SC_kagome` 等文件。

---

## 4. 运行前必须检查的 6 件事（新手最关键）

1. QE 输入 `&CONTROL` 中有统一 `prefix`（本目录已设为 `kagome_221`）。
2. `scf.in` 与 `band.in` 的 `prefix` 必须一致。
3. `outdir` 路径在 SCF 与 bands 中一致。
4. 赝势文件路径可访问（`pseudo_dir` + 实际 `.upf` 文件）。
5. 你运行脚本的目录要正确（建议在仓库根目录运行）。
6. 你的 QE 可执行命令要可用（例如 `pw.x` 或 `mpirun -np 32 pw.x`）。

---

## 5. 一条命令能不能自动全做完？

可以。

### 仅后处理（不自动跑 QE）
```bash
python tutorials/QuantumEspresso/kagome/run_banduppy_qe_kagome.py
```

### 自动跑 QE + unfold + 画图
```bash
python tutorials/QuantumEspresso/kagome/run_banduppy_qe_kagome.py --run-all
```

> `--run-all` 前提：你的 `QE_EXE` 可执行且环境已配置好。

---

## 6. 推荐给初学者的“稳妥跑通顺序”

### Step 1：先只做后处理链路检查
先不加 `--run-all`，确认脚本能读取 `.save`。

### Step 2：如果提示找不到 `.save`
说明 QE 结果还没准备好，先单独跑：

```bash
cd tutorials/QuantumEspresso/kagome
pw.x -input scf.in > scf.out
pw.x -input band.in > band.out
```

（或使用脚本自动模式 `--run-all`）

### Step 3：再执行 unfold
回到仓库根目录再跑脚本。

---

## 7. 关键输出文件说明

在 `tutorials/QuantumEspresso/kagome/results/` 你会得到：

- `kpoints_unfolded_kagome.dat`：展开后路径坐标；
- `bandstructure_unfolded_kagome.dat`：展开后的能带与权重；
- `unfolded_bandstructure_kagome.png`：可视化图。

---

## 8. 常见报错对应处理

### 报错 1：`FileNotFoundError: ... kagome_221.save`
- 原因：QE 没跑成功，或 `prefix/outdir` 不一致。
- 处理：先检查 `scf.out`/`band.out` 是否正常结束，再核对 `prefix/outdir`。

### 报错 2：`pw.x` not found
- 原因：QE 未加载到当前环境。
- 处理：改 `QE_EXE` 为你的真实命令（含 MPI 前缀）。

### 报错 3：图像很“糊”或很“粗”
- 原因：`smear/fatfactor/nE` 与数据范围不匹配。
- 处理：在脚本中调整 `smear`、`fatfactor`、`nE` 与 `E_MIN/E_MAX`。

---

## 9. 参数最小改动指南

你通常只需改这些：

1. `QE_EXE`：并行与可执行命令；
2. `E_FERMI`, `E_MIN`, `E_MAX`：作图区间；
3. `USE_EXISTING_SC_KPOINTS`：是否使用你现有超胞 k 点；
4. （可选）`PC_BZ_PATH` 与 `NPOINTS_PER_SEG`：仅在自动生成路径模式下。

---

## 10. 给你的直接结论

你前面提出的疑问是正确的：

- 你已经提供了超胞 k 点时，不应强制“原胞→超胞生成”；
- 本教程和脚本现在已按仓库真实用法区分两种模式；
- 新手建议先用“你自己的超胞 k 点 + 先跑通后处理”，再尝试自动映射模式做对照。

如果你愿意，我下一步可以再给你补一个“逐行解释 `run_banduppy_qe_kagome.py`”版本（每个变量改哪里、会影响什么、如何判断是否跑对）。

---

## 11. 你应该逐步运行哪些“计算”？（QE 做什么，BandUPpy 做什么）

下面按“计算任务”拆开讲：

### 11.1 QE-1：SCF（自洽电荷）
**目的**：得到稳定电荷密度和基础电子结构。

- 输入：`scf.in`
- 产物：`<prefix>.save`（以及电荷密度等）

命令（手动模式）：
```bash
cd tutorials/QuantumEspresso/kagome
pw.x -input scf.in > scf.out
```

### 11.2 QE-2：bands（本教程实际使用）
**目的**：在你设定的超胞高对称路径上得到可用于 unfold 的波函数信息。

- 输入：`band.in`（或脚本生成的 `band_run.in`）
- 产物：更新后的 `<prefix>.save` 与 band 相关输出

命令（手动模式）：
```bash
pw.x -input band.in > band.out
```

> 说明：如果你未来改成 `calculation='nscf'`，那也是非自洽计算，但与本教程当前 `bands` 输入不完全等价。

> 若你使用脚本自动模式（`--run-all`），它会先跑 `scf_run.in`，再生成并跑 `band_run.in`。

### 11.3 BandUPpy-1：读取 QE 波函数
**目的**：把 QE 的 `<prefix>.save` 解析成 BandUPpy 可操作对象。

对应代码：
```python
bands = banduppy.BandStructure(code="espresso", spinor=False, prefix=PREFIX)
```

### 11.4 BandUPpy-2：Unfold（核心反折叠计算）
**目的**：把超胞能带权重投影回原胞 BZ。

对应代码：
```python
unfolded_bandstructure, kpline = unfold.Unfold(...)
```

输出：
- `results/kpoints_unfolded_kagome.dat`
- `results/bandstructure_unfolded_kagome.dat`

### 11.5 BandUPpy-3：作图
**目的**：把 unfolded 结果可视化。

对应代码：
```python
plotter.plot_ebs(...)
```

输出：
- `results/unfolded_bandstructure_kagome.png`

---

## 12. `run_banduppy_qe_kagome.py` 逐行解释（按代码块）

> 说明：你要求“逐行解释”，这里按**连续代码行号**逐段解释。行号以当前仓库版本为准。

### 12.1 文件头与导入（第 1–19 行）
- 1–9：脚本说明（用途：QE + BandUPpy 的 Kagome 反折叠流程）。
- 11：`from __future__ import annotations`，仅影响类型注解行为。
- 13–16：标准库导入（复制文件、路径、命令行参数、子进程执行）。
- 18–19：第三方包 `banduppy`、`numpy`。

### 12.2 用户开关与核心参数（第 21–56 行）
- 23：`USE_EXISTING_SC_KPOINTS = True`，默认用你 `band.in` 里的超胞 `K_POINTS`。
- 27：`AUTO_RUN_ALL = "--run-all" in sys.argv`，是否自动跑 QE。
- 29–30：`RUN_QE_SCF/RUN_QE_BANDS` 与 `AUTO_RUN_ALL` 绑定。
- 33–35：读取波函数、是否 unfold、是否画图开关。
- 38：`QE_EXE`，QE 命令入口（你可改成 MPI 形式）。
- 41：`SUPER_CELL`，2×2×1 超胞矩阵。
- 44–51：仅在“自动生成路径模式”才会用到的原胞路径参数。
- 54–56：绘图能量窗口设置。

### 12.3 路径初始化（第 58–68 行）
- 59：`THIS_DIR` 指向当前脚本目录。
- 60–61：确保 `results/` 存在。
- 63–66：定义 `scf.in`、`band.in` 模板与脚本生成输入文件名。
- 68：打印 BandUPpy 版本，便于记录环境。

### 12.4 Step 1：准备超胞 k 点（第 70–103 行）
- 71：初始化 `Unfolding` 对象（核心类）。
- 73–80（默认路径）：
  - 读取 `band.in`；
  - 检查是否存在 `K_POINTS`；
  - 直接抽取并复用你提供的超胞 `K_POINTS`。
- 81–103（可选路径）：
  - 调用 `generate_SC_Kpts_from_pc_k_path()` 从原胞路径生成超胞路径；
  - 读取生成的 `KPOINTS_SC_kagome`，供后续 `band_run.in` 使用。

### 12.5 Step 2：可选执行 QE（第 105–119 行）
- 107–110：若开启 `RUN_QE_SCF`，复制 `scf.in` 为 `scf_run.in` 后执行 QE。
- 112–119：若开启 `RUN_QE_BANDS`：
  - 读取 `band.in` 文本；
  - 用准备好的 `kpoints_sc` 替换其 `K_POINTS` 段；
  - 写入 `band_run.in` 并执行 QE。

### 12.6 Step 3：读取波函数 + unfold（第 121–156 行）
- 122–123：如果没开 `--run-all`，给出提示。
- 125–133：读取 QE 波函数：
  - `PREFIX = tutorials/QuantumEspresso/kagome/kagome_221`
  - 从 `<prefix>.save` 读取 band 数据。
- 135–151：执行 `Unfold()`，并保存 unfolded k 点和能带数据到 `results/`。
- 152–156：若不开 `DO_UNFOLD`，则从已有 `.dat` 文件读取结果。

### 12.7 Step 4：画图（第 158–178 行）
- 159：初始化 `Plotting`。
- 160–177：`plot_ebs()` 绘制 fatband 图，使用你上面设定的能量窗口与标签。
- 163：输出图片名 `unfolded_bandstructure_kagome.png`。

### 12.8 结束信息（第 180 行）
- 打印完成提示，表示流程走通。

---

## 13. 给你的“最短可执行清单”

如果你要最稳妥地一步步做：

1. 先手动 QE：
```bash
cd tutorials/QuantumEspresso/kagome
pw.x -input scf.in > scf.out
pw.x -input band.in > band.out
```
2. 回仓库根目录做 unfold+画图：
```bash
cd /workspace/banduppy
python tutorials/QuantumEspresso/kagome/run_banduppy_qe_kagome.py
```

如果你要一条命令全流程：
```bash
python tutorials/QuantumEspresso/kagome/run_banduppy_qe_kagome.py --run-all
```
