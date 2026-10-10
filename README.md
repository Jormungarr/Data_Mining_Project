# 流感季公营医院急症服务压力

香港公营医院急症服务的周度面板数据集，以及构建它的可复现数据管道。

**研究问题**：流感活动强度的上升如何转化为香港公营医院急症服务的需求压力？
这种传导在不同医院之间是否存在系统性差异？

| | |
|---|---|
| 主分析表 | `data/processed/panel_hospital_week.csv` |
| 规模 | **2,448 行 × 34 列**（17 间医院 × 144 周，平衡面板） |
| 时间范围 | 2019-12-07 → 2026-08-08（8 个流感季） |
| 数据来源 | 卫生署、医院管理局、香港天文台（共 29 个公开数据文件） |
| 变量字典 | [`data/processed/data_dictionary.csv`](data/processed/data_dictionary.csv) |
| **数据结构详解** | **[`DATA_GUIDE.md`](DATA_GUIDE.md)** ← 动手前请先读 |

---

## 快速开始

**只想拿数据**：`data/processed/` 里已经是成品，直接用。

**想自己重新合并**：

```bash
./pipeline/run_all.sh          # 构建 → 验证，约 10 秒
```

首次运行会自动用 `uv` 创建 `.venv` 并安装依赖（Python 3.12）。
**整个过程不联网** —— 原始数据已随仓库提供在 `data/raw/`。

```bash
./pipeline/run_all.sh                # 构建 + 验证
./pipeline/run_all.sh --check-only    # 只检查 data/raw/ 完整性
```

管道直接读取 `data/raw/`，不下载任何东西。若要更新到最新官方数据，
按 [`data/raw/SOURCES.md`](data/raw/SOURCES.md) 手动下载覆盖对应文件即可。

管道是**确定性**的。在同一批原始数据上重复运行，产出的 CSV 逐字节一致
（已验证：冷启动重建后 6 个产出文件的 SHA256 完全相同）。

---

## 目录结构

```
.
├── README.md                     本文档：快速开始与管道说明
├── DATA_GUIDE.md                 ★ 数据集结构、变量详解、探索空间
├── LICENSE                       MIT + 数据版权说明
│
├── pipeline/                     ★ 数据管道（可复现的全部逻辑）
│   ├── run_all.sh                一键驱动
│   ├── 01_build.py               清洗、聚合、合并 → 分析数据集
│   └── 02_validate.py            结构/时间/一致性/分布 四类检查
│
├── data/
│   ├── raw/                      原始文件（逐字节保存，从不改写）
│   │   ├── SOURCES.md            ★ 数据来源与下载链接
│   │   ├── _manifest.json        URL / 字节数 / SHA256 / 抓取时间
│   │   ├── _provenance.json      data.gov.hk 数据集官方元数据
│   │   └── flu/  ha/  hko/
│   └── processed/                产出表（可由管道重建）
│
├── out/
│   └── validation_report.txt     数据验证报告（40+ 项断言）
│
└── pyproject.toml / uv.lock      依赖锁定
```

**`data/raw/` 从不被改写。** 所有清洗都发生在 `01_build.py`。
这意味着任何时候都可以从原始文件重新推导结果，且能看到用了哪个版本的数据。

---

## 数据来源

| # | 来源 | 数据集 | 频率 | 用途 |
|---|---|---|---|---|
| 1 | 卫生署 卫生防护中心 | [流感速递图表数据](https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express) | 周 | 解释变量 |
| 2 | 医院管理局 | [服务需求高峰统计数字](https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge) | 日 | 结果变量 |
| 3 | 医院管理局 | [住院及日间住院服务量](https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ipdp) | 财政年度 | 协变量 |
| 4 | 医院管理局 | [门诊及社区服务量](https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ambulatory-community) | 财政年度 | 协变量 |
| 5 | 医院管理局 | [医院/机构名录](https://data.gov.hk/sc-data/dataset/hospital-hadata-health-care-facilities) | 季 | 空间维度 |
| 6 | 香港天文台 | [开放数据 API](https://data.weather.gov.hk/weatherAPI/doc/HKO_Open_Data_API_Documentation.pdf) `CLMTEMP`/`CLMMAXT`/`CLMMINT` | 日 | 协变量 |

data.gov.hk 上的**官方元数据**（标题、提供机构、更新频率）在下载时一并存档到
`data/raw/_provenance.json`。每个文件的 URL 与 SHA256 见 `data/raw/_manifest.json`。

---

## 管道细节

### 01_build.py

按 S0–S6 七步执行，每一步都有日志：

| 步骤 | 内容 |
|---|---|
| **S0** | 比对 `data/raw/_manifest.json` 中的 SHA256，报告缺失或被改动的文件（仅提示，不中断） |
| **S1** | 读入并解析 6 个来源 |
| **S2** | 统一医院/联网名称（跨来源对照表，见源码 `HOSPITAL_NAME_MAP`） |
| **S3** | HA 逐日数据 → 按流感周界（周日至周六）聚合成 `(联网, 医院, 周)` 均值 |
| **S4** | 挂载医院年度容量协变量（财政年度 4 月制对齐） |
| **S5** | 天文台逐日气温 → 按同一周界聚合成周均值 |
| **S6** | 合并、排序列、前向填充病床数、生成质量标记列、写出 |

关键处理约定集中在源码顶部常量区：周的定义统一采用流感速递的 `From`/`To`；
跨来源医院名称映射；病床数与年服务量的年度前向填充。

**数据处理中踩过的坑（若自行合并需同样处理）**见 [`DATA_GUIDE.md` 第 5 节](DATA_GUIDE.md#5-数据处理中已解决的坑)。

### 02_validate.py

四类检查，共 40+ 项断言，任一失败则退出码为 1（可用于 CI）：

| 类别 | 内容 |
|---|---|
| **A 结构** | 行数 2,448、17 院、144 周、面板平衡、主键唯一、列数 |
| **B 时间** | 周界恰为 7 天、季节标签、断档被正确标记、季节内周序连续编号 |
| **C 一致性** | 各院之和 vs HA Overall、协变量零缺失、独立复算原始文件行数 |
| **D 分布** | 取值范围、缺失率、流感变量的结构性常量性、已知缺失模式 |

最新报告见 [`out/validation_report.txt`](out/validation_report.txt)。

---

## 产出表

| 文件 | 规模 | 说明 |
|---|---|---|
| `panel_hospital_week.csv` | 2,448 × 34 | **主分析表**（医院 × 周） |
| `hk_weekly.csv` | 144 × 23 | 全港汇总周序列（HA Overall） |
| `hospital_beds_annual.csv` | 医院 × 财政年度 | 病床数宽表（FY2008-09 起） |
| `ae_attendances_annual.csv` | 医院 × 财政年度 | 急症室年服务量（FY2008-09 起） |
| `hospital_directory.csv` | 44 个机构 | 名录、联网、是否有急症室、地址、经纬度 |
| `data_dictionary.csv` | 34 行 | 变量字典（类型、单位、缺失数） |

变量含义、样本结构、探索空间与建模注意事项：
**→ [`DATA_GUIDE.md`](DATA_GUIDE.md)**

---

## 复现验证

```bash
# 从 GitHub 全新克隆后运行（不联网）
git clone <repo> && cd <repo> && ./pipeline/run_all.sh
→ raw 完整性 29/29 一致
→ S0–S6 构建完成
→ 四类检查全部通过
→ 6 个产出文件的 SHA256 与上游仓库逐个一致

# 只检查原始数据
./pipeline/run_all.sh --check-only
→ 与清单一致 29/29
```

---

## 环境

`pyproject.toml` + `uv.lock` 锁定依赖：

```
Python 3.12
pandas 3.0.6    numpy 2.5.3    scipy 1.18.1    statsmodels 0.15.0
matplotlib 3.11.2    requests 2.34.2    lxml 6.1.3
```

只需 `pandas` 即可跑通整条管道，且**不需要联网**（其余依赖为后续建模所需）。

在受限环境（如沙箱）中，`uv` 的默认缓存目录可能不可写，此时设置：

```bash
export UV_CACHE_DIR="$PWD/.uv-cache"
```
`run_all.sh` 已默认使用该目录。
