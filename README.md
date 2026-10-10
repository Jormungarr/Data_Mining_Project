# 流感季公营医院急症服务压力

数据管道与分析数据集。

**研究问题**：流感活动强度的上升如何转化为香港公营医院急症服务的需求压力？
这种传导在不同医院之间是否存在系统性差异？

---

## 快速开始

```bash
cd project
./pipeline/run_all.sh          # 下载 → 校验 → 构建 → 验证，约 2 分钟
```

首次运行会自动用 `uv` 创建 `.venv` 并安装依赖（Python 3.12）。

三种运行模式：

```bash
./pipeline/run_all.sh              # 增量：已有的原始文件跳过下载
./pipeline/run_all.sh --fresh      # 彻底重来：清空 data/ 后从零重建
./pipeline/run_all.sh --check-only # 离线：只校验本地文件，不联网
```

管道是**确定性**的。在同一批原始数据上重复运行，产出的 CSV 逐字节一致
（已验证：冷启动重建后 6 个产出文件的 SHA256 完全相同）。

---

## 数据来源

全部为公开数据，共 29 个文件，约 5.6 MB。

| # | 来源 | 数据集 | 粒度 | 用途 |
|---|---|---|---|---|
| 1 | 卫生署 卫生防护中心 | [流感速递图表数据](https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express) | 周 | 解释变量 |
| 2 | 医院管理局 | [服务需求高峰统计数字](https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge) | 日 | 结果变量 |
| 3 | 医院管理局 | [住院及日间住院服务量（病床数）](https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ipdp) | 财政年度 | 协变量 |
| 4 | 医院管理局 | [门诊及社区服务量（急症室）](https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ambulatory-community) | 财政年度 | 协变量 |
| 5 | 医院管理局 | [医院/机构名录](https://data.gov.hk/sc-data/dataset/hospital-hadata-health-care-facilities) | 静态 | 联网、坐标 |
| 6 | 香港天文台 | [开放数据 API](https://data.weather.gov.hk/weatherAPI/doc/HKO_Open_Data_API_Documentation.pdf) `CLMTEMP` / `CLMMAXT` / `CLMMINT` | 日 | 协变量（气温） |

data.gov.hk 上的**官方元数据**（标题、提供机构、更新频率）会在下载时一并存档到
`data/raw/_provenance.json`。

---

## 目录结构

```
project/
├── README.md                     本文档
├── RECOMMENDED.md                研究设计与数据规格说明
├── REPORT.md                     三个候选方案的可行性核查（历史记录）
├── PROPOSAL3.md                  方案三早期分析（历史记录）
│
├── pipeline/                     ★ 数据管道（可复现的全部逻辑）
│   ├── run_all.sh                一键驱动
│   ├── 01_download.py            下载 + SHA256 清单 + 元数据存档
│   ├── 02_build.py               清洗、聚合、合并 → 分析数据集
│   └── 03_validate.py            结构/时间/一致性/分布 四类检查
│
├── data/
│   ├── raw/                      原始文件（逐字节保存，从不改写）
│   │   ├── _manifest.json        URL / 字节数 / SHA256 / 抓取时间
│   │   ├── _provenance.json      data.gov.hk 数据集官方元数据
│   │   └── flu/  ha/  hko/
│   ├── processed/                ★ 产出（可安全删除，由管道重建）
│   └── _exploratory/             探索阶段的下载（不参与管道）
│
├── out/
│   └── validation_report.txt     验证报告
│
├── scripts/exploratory/          探索阶段脚本（方案筛选、可行性测试）
└── pyproject.toml / uv.lock      依赖锁定
```

**`data/raw/` 从不被改写。** 所有清洗都发生在 `02_build.py`。
这意味着任何时候都可以从原始文件重新推导结果，且能看到用了哪个版本的数据。

---

## 管道细节

### 01_download.py

- 清单式声明全部 29 个资源（URL + 本地路径 + 用途），见源码 `build_manifest()`
- 幂等：已存在且 SHA256 匹配则跳过；`--force` 强制重下
- 每个文件记录 `url` / `bytes` / `sha256` / `retrieved_at` 到 `_manifest.json`
- 拦截明显的错误响应（HKO 参数错误、HTML 404 页）
- `--check` 可完全离线地校验本地文件完整性

### 02_build.py

按 S1–S6 六步执行，每一步都有日志：

| 步骤 | 内容 |
|---|---|
| **S1** | 读入并解析 6 个来源 |
| **S2** | 统一医院/联网名称（跨来源对照表，见源码 `HOSPITAL_NAME_MAP`） |
| **S3** | HA 逐日数据 → 按流感周界（周日至周六）聚合成 `(联网, 医院, 周)` 均值 |
| **S4** | 挂载医院年度容量协变量（财政年度 4 月制对齐） |
| **S5** | 天文台逐日气温 → 按同一周界聚合成周均值 |
| **S6** | 合并、排序列、前向填充病床数、生成质量标记列、写出 |

关键处理约定（全部集中在源码顶部常量区，便于审阅）：

- **周的定义**一律采用流感速递的 `From`/`To`；`To` 为该周最后一天（周六）。
  所有其它来源都对齐到这个边界。
- **医院名称**跨来源不一致，必须显式对照。例如 HA 高峰统计用
  `Ruttonjee & Tang Shiu Kin Hospitals`，而病床年表在 2017-18 前后改用
  `Ruttonjee Hospital` —— 不处理会导致该院整行静默丢失。
- **病床数与年服务量**只发布到 FY2024-25，之后沿用最后一年（病床是慢变量）。
- **跨季节断档**：HA 从 2023-24 起停止逐日发布，导致周序列出现空档。
  这由 `prev_gap_days` 列显式标记（见下）。

### 03_validate.py

四类检查，共 40+ 项断言，任一失败则退出码为 1（可用于 CI）：

| 类别 | 内容 |
|---|---|
| **A 结构** | 行数 2,448、17 院、144 周、面板平衡、主键唯一、列数 |
| **B 时间** | 周界恰为 7 天、季节标签、断档被正确标记、季节内周序连续编号 |
| **C 一致性** | 各院之和 vs HA Overall、协变量零缺失、独立复算原始文件行数 |
| **D 分布** | 取值范围、缺失率、流感变量的结构性常量性、已知缺失模式 |

---

## 主分析表

`data/processed/panel_hospital_week.csv` — **2,448 行 × 34 列**
（17 间医院 × 144 周的平衡面板，分属 8 个流感季）

### 列分组

| 组 | 列数 | 列名 |
|---|---|---|
| 标识 | 6 | `hospital`, `cluster`, `fy`, `season`, `week_start`, `week_end` |
| **结果变量** | 4 | `ae_first_attend`, `ae_to_med_ip`, `med_bed_occ_rate`, `ped_bed_occ_rate` |
| **解释变量** | 9 | `ILI_PMP`（主）, `ILI_AED`, `Adm_65`, `Adm_All`, `Severe65`, `flu_H1`, `flu_H3`, `flu_B`, `flu_AandB` |
| 协变量 | 8 | `beds_acute`, `beds_infirmary`, `beds_mental`, `beds_mh`, `ae_annual`, `with_AE`, `lat`, `lon` |
| 协变量（气温） | 3 | `temp_mean`, `temp_max`, `temp_min` |
| 数据质量 | 4 | `temp_days`, `days`, `week_in_season`, `prev_gap_days` |

完整变量字典见 `data/processed/data_dictionary.csv`（含每列的类型、单位、缺失数）。

### 样本结构

面板本身**完全平衡**（无缺行），但**各结果变量的可用样本不同**：

| 结果变量 | 类型 | 可用行 | 缺失 | 缺失原因 |
|---|---|---|---|---|
| `ae_first_attend` | 计数 | **2,448** | 0% | — |
| `ae_to_med_ip` | 计数 | 2,302 | 6.0% | North Lantau 无内科住院服务 |
| `med_bed_occ_rate` | 有界比例 | 2,304 | 5.9% | 同上 |
| `ped_bed_occ_rate` | 有界比例 | 1,597 | 34.8% | 仅 11 间医院设有儿科 |

### 三个必须知道的结构特征

**1. 解释变量无截面变异。**
9 个流感变量都是全港单一时间序列 —— 同一周内 17 家医院取到完全相同的值
（验证脚本已断言这一点）。这意味着它们只能解释「全港共同的周际波动」，
不能解释「为什么 A 院比 B 院压力大」。后者只能靠医院固定效应与容量协变量。

**2. 时间轴不连续。**
`T = 144` 不是连续的 144 周，而是 8 个互不相连的冬季窗口：

```
season     周数   起            止              断档
2019-20     13   2019-12-07   2020-02-29      连续
2020-21     22   2020-12-05   2021-05-01      连续
2021-22     22   2021-12-04   2022-04-30      连续
2022-23     30   2022-12-03   2023-06-24      连续
2023-24     26   2023-12-23   2024-06-22      断档 1 处（14 天）
2024-25     17   2024-12-21   2025-05-10      断档 1 处（35 天）
2025-26     11   2025-12-27   2026-04-11      断档 2 处（21、28 天）
2026-27      3   2026-07-25   2026-08-08      连续
```

> **构造滞后变量时必须按 `season` 分组**，并检查 `prev_gap_days == 7`。
> 直接对全表 `shift(1)` 会在 4 处断档上把数周前的值当成「上一周」。

**3. `days` 记录该周实际有几天数据。**
HA 个别周发布不完整（最少只有 1 天），周均值因此波动更大。
`days < 7` 的行共 316 行，可用作加权或稳健性筛选（只保留 `days == 7` 剩 2,108 行）。

---

## 其余产出

| 文件 | 规模 | 说明 |
|---|---|---|
| `hk_weekly.csv` | 144 × 23 | 全港汇总周序列（HA Overall），做总体趋势图 |
| `hospital_beds_annual.csv` | 医院 × 财政年度 | 病床数原始宽表（FY2008-09 起） |
| `ae_attendances_annual.csv` | 医院 × 财政年度 | 急症室年服务量（FY2008-09 起） |
| `hospital_directory.csv` | 44 个机构 | 名录、联网、是否有急症室、地址、经纬度 |
| `data_dictionary.csv` | 34 行 | 逐列变量字典 |

---

## 复现验证

已执行的验证：

```bash
# 1. 冷启动重建（删掉 raw 与 processed 后从零跑）
./pipeline/run_all.sh --fresh
→ 29 个文件全部下载成功，四类检查全部通过

# 2. 产出哈希对比（冷启动前后）
ae_attendances_annual.csv    b9218b5682e66ec4...
data_dictionary.csv          9a004d5d35785e0f...
hk_weekly.csv                b84871e70c2580ae...
hospital_beds_annual.csv     dd69b8a83c32c4a5...
hospital_directory.csv       6c926fa423a1c221...
panel_hospital_week.csv      d300c67041ef25a0...
→ 完全一致

# 3. 原始文件离线校验
./pipeline/run_all.sh --check-only
→ 全部 29 个文件 SHA256 校验通过
```

---

## 环境

`pyproject.toml` + `uv.lock` 锁定依赖：

```
Python 3.12
pandas 3.0.6    numpy 2.5.3    scipy 1.18.1    statsmodels 0.15.0
matplotlib 3.11.2    requests 2.34.2    lxml 6.1.3
```

只需 `pandas` 即可跑通整条管道（其余为后续建模与探索所需）。

在受限环境（如沙箱）中，`uv` 的默认缓存目录可能不可写，此时设置：

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
```
`run_all.sh` 已默认使用该目录。

---

## 已知限制

1. **时间不连续** — 8 个冬季窗口，不能当作连续时间序列做 ARIMA / STL 全日历年分析。
   应以季节固定效应分层，把每个冬季视为独立的高峰事件。
2. **解释变量为生态层面** — 流感监测是全港指标，不是医院服务范围级别。
   这是「全港流感活动 → 各院压力」的设计，不支持个体层面的因果推断。
3. **COVID 期间混淆** — 2020–2022 年口罩令与社交距离同时压低了流感与急症需求，
   需要季节固定效应与剔除该期间的稳健性检验。
4. **无死亡分层数据** — 政府发布的月度死亡数不含年龄与死因维度，
   因此结果变量限于服务量与占用率，不含死亡。
5. **病床数为年度** — 医院容量按财政年度发布，无法捕捉年内的容量变化。

---

## 历史文档

`REPORT.md` 与 `PROPOSAL3.md` 记录了方案筛选过程（包括三个候选方案各自的
可行性核查结果与失败原因），保留作为决策依据。`scripts/exploratory/` 是对应的
探索脚本。它们**不参与**主管道，可安全忽略。
