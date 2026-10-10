# 三个方案的 data.gov.hk 可行性核查报告

> 核查方式：ego-browser 实地浏览 data.gov.hk/cs + 调用站点 CKAN API 定位数据集 +
> 下载真实文件 + 用 `uv` 隔离环境写脚本实测拼接。
> 环境：`project/.venv`（Python 3.12.14，pandas 3.0.6 / numpy 2.5.3 / statsmodels 0.15.0 / lxml 6.1.3）

---

## 0. 一句话结论

| 方案 | 结论 | 关键原因 |
| --- | --- | --- |
| 方案一 交通效率 × 空气质量 | ❌ **核心拼接不成立** | 車程時間資料**只有年度**（2023/2024/2025 三个横截面），无月度/季度；AQHI 是逐小时。时间粒度差 3 个数量级 |
| 方案二 旅游 × 社区商业 | ⚠️ **需换设计** | 酒店入住率（月度+分区）可用；但**食肆牌照没有发牌日期**，只有到期日 →「每月新增持牌食肆」做不出来 |
| 方案三 公共卫生负担 | ⚠️ **需换结局变量** | 流感速递（周）质量很好；但**死亡统计没有「周 × 65+ × 呼吸系统疾病」这个切片** |

三个方案里，**方案三最接近可行**，方案二次之，方案一按原设计不可行。

---

## 1. 数据集定位结果（浏览器实地确认）

在 data.gov.hk 上用中文关键词逐个找到对应数据集，官方页面直接写明**更新频率**：

| 方案 | 你的说法 | 站点实际数据集 | 数据集 ID | 官方更新频率 |
| --- | --- | --- | --- | --- |
| 一 | 車輛車程時間資料 | [车辆车程时间资料](https://data.gov.hk/sc-data/dataset/hk-td-tis_34-car-journey-time-data) | `hk-td-tis_34-car-journey-time-data` | **每年** |
| 一 | 過去空氣質素健康指數記錄 | [过去空气质素健康指数记录](https://data.gov.hk/sc-data/dataset/hk-epd-airteam-past-record-of-air-quality-health-index-tc) | `hk-epd-airteam-past-record-of-air-quality-health-index-tc` | 每六个月 |
| 一/二 | 2021年人口普查 | [2021年人口普查（按區議會分區）](https://data.gov.hk/sc-data/dataset/hk-censtatd-census_geo-2021-population-census-by-dcd) | `hk-censtatd-census_geo-2021-population-census-by-dcd` | 一次性 |
| 二 | 酒店房間入住率 | [按地区划分的酒店房间入住率](https://data.gov.hk/sc-data/dataset/hk-cstb-cstb_tc-tc-hotel-room-occupancy-rate-by-district) | `hk-cstb-cstb_tc-tc-hotel-room-occupancy-rate-by-district` | 每月 |
| 二 | 食肆牌照 | [食肆牌照](https://data.gov.hk/sc-data/dataset/hk-fehd-fehdlmis-restaurant-licences) | `hk-fehd-fehdlmis-restaurant-licences` | 每日上午9时 |
| 三 | 流感速遞圖表數據 | [流感速递图表数据](https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express) | `hk-dh-chpsebcddr-flu-express` | 每周 |
| 三 | 死亡統計 | [死亡统计](https://data.gov.hk/sc-data/dataset/hk-dh-dh_ncddhss-ncdd-dataset-3) | `hk-dh-dh_ncddhss-ncdd-dataset-3` | 当有需要时 |

截图见 `out/shots/*.png`。

---

## 2. 方案一：交通效率与环境关联 —— ❌ 不成立

**脚本**：`scripts/20_test_f1.py`　**日志**：`out/20_test_f1.log`

### 2.1 实测到的车程时间文件结构

下载了全部 48 个 CSV（8 个版面 × 3 个年度），表头只有两种：

```
TABLE2(O-D ROUTE): Origin - Destination | Start | Via | Finish | Distance(km) | Journey Time(minutes)
TABLE4(STREET)   : Road/Street | Section Studied (between) | Distance (km) | Journey Time (minutes)
```

**两张表都没有任何月份、季度或日期欄位。** 唯一的时间信息在标题里（"…2024"）和文件名里。

```
可用的时间點：
  TABLE2(O-D ROUTE)  2023: 8 檔  164 條路線      2024: 8 檔  164 條      2025: 8 檔  164 條
  TABLE4(STREET)     2023: 8 檔  630 個路段      2024: 8 檔  633 個      2025: 8 檔  633 個
  → 年度清單 = [2023, 2024, 2025]，就这 3 个
```

这与官网写的「更新频率：**每年**」、描述「香港选定路线繁忙时段**平均**行车时间」完全一致。

### 2.2 与 AQHI 的粒度对比

| 资料 | 时间键 | 粒度 | 覆盖 |
| --- | --- | --- | --- |
| 车程时间 | 年份 | **年** | 2023–2025（3 期） |
| AQHI | 日期 + 小时 + 监测站 | **小时** | 2013-12 → 2026-06（151 个月，109,416 笔，18 个站） |
| 人口普查 | 年份 | **一次性** | 2021（1 期） |

- 年度交集 = `[2023, 2024, 2025]`，**只有 3 期**。
- 若以「路段 × 方向」为观测单位，每条路段只有 3 个观测点 → 无法做任何时间序列建模。
- 你原设计的「按天聚合 AQHI → 月度/季度均值 → 与车程时间连接」在技术上做不到，因为车程端**根本没有月/季这一层**。

### 2.3 地理键也对不上

- 车程时间：以**路段**为单位，表内没有分区欄位；文件名里的「Hong Kong Island / Kowloon / NT」只是版面分组。
- AQHI：18 个**监测站**（Central/Western、Tap Mun、Causeway Bay…），不是 18 区。
- 人口普查：18 个**区议会分区**。

三者没有共同主键，需要人工建立「路段 ↔ 监测站 ↔ 分区」对照表。

### 2.4 有没有替代？

我额外核查了几条常见替代路线，**都不行**：

| 替代资料 | 结果 |
| --- | --- |
| [Monthly Traffic and Transport Digest](https://data.gov.hk/sc-data/dataset/hk-td-tis_17-monthly-traffic-and-transport-digest-csv)（234 个资源） | 名为 monthly，但含「Journey」的表全是**乘客行程量**（Passenger Journeys），**没有任何行车时间/车速序列** |
| [Journey time indicators (2nd Generation)](https://data.gov.hk/sc-data/dataset/hk-td-sm_8-journey-time-indicators-v2) | 只有 XML 即时接口（`Journeytimev2.xml`），**无历史** |
| [Traffic Data of Strategic/Major Roads](https://data.gov.hk/sc-data/dataset/hk-td-sm_4-traffic-data-strategic-major-roads) | 实测抓取：`<date>2026-10-10</date>` + 30 秒时段 → **只是当下快照**，无历史 |
| [Journey Time Indicators (City Dashboard Version)](https://data.gov.hk/sc-data/dataset/hk-dpo-datagovhk2-city-dashboard-journey-time) | 站点已明写「**This dataset is no longer being updated**」 |
| [Annual Traffic Census](https://data.gov.hk/sc-data/dataset/hk-td-sm_5-annual-traffic-census-survey-data) | 只有**车流量**，且是年度调查 |

### 2.5 可行的改法（若要保留「交通 × 环境」主题）

1. **换主资料**：放弃港府车程时间，改用 **TomTom / HERE 等 API** 自行抓取车程时间序列（但这已不是 data.gov.hk 题目）。
2. **换主题**：把「车程时间」换成有月度粒度的交通代理变量 —— 例如
   `hk-td-tis_17` 的公共交通载客量、车辆登记量（月度，2026 前完整）+ AQHI 月度均值；
   问题是失去「行车时间」这个落点。
3. **改做横截面**：用 2023/2024/2025 三个年度的车程时间 + 年度 AQHI 均值，
   做 **n=3 的描述性对比**（不能做回归）。作为课程作业太单薄。

> **结论：方案一建议放弃或彻底改题。**

---

## 3. 方案二：旅游业复苏 × 社区商业活力 —— ⚠️ 需换设计

**脚本**：`scripts/21_test_f2.py`　**日志**：`out/21_test_f2.log`

### 3.1 酒店入住率 ✔ 可用

```
整体月度 : 60 个月   202108 → 202607
分区月度 : 60 行 × 9 欄（8 个旅游区）
```
分区：Central/Western、Wan Chai、Eastern & Southern HK、Tsim Sha Tsui、
Yau Ma Tei/Mong Kok、other Kowloon、New Territories、Island。

⚠️ **这是 8 个「旅游区」分组，不是 18 个区议会分区**，与人口普查对不上（多对一、覆盖不全）：

```
Central / Western      -> Central and Western      （1:1）
Wan Chai               -> Wan Chai                 （1:1）
Eastern & Southern HK  -> Eastern + Southern       （1:2 合并）
Tsim Sha Tsui          -> Yau Tsim Mong            （并入）
Yau Ma Tei / Mong Kok  -> Yau Tsim Mong            （并入，TSK 与 YMT 在旅游区里反而分开）
other Kowloon          -> 深水埗/黄大仙/观塘…      （定义模糊）
New Territories        -> 9 个新界区合并
Island                 -> Islands                  （1:1）
```

### 3.2 食肆牌照 ✘ 关键字段缺失

下载真实 XML（4.9 MB，17,294 条牌照），用 lxml 枚举**全部**字段：

```
<LP> 的子元素统计：
{'TYPE': 17294, 'DIST': 17294, 'LICNO': 17294, 'SS': 17294,
 'ADR': 17294, 'INFO': 17294, 'EXPDATE': 17294}

日期类欄位 = ['EXPDATE']   ← 只有「到期日」，没有「发牌日期」
```

这是**单一时点快照**（`<GENERATION_DATE>2026-10-10</GENERATION_DATE>`，每日上午 9 时更新）。
它**能**回答：

- ✔ 「截至某日，各区有多少持牌食肆」（本快照：湾仔 1,774、油尖 1,894、中西区 1,790…）

它**不能**回答你的核心问题：

- ✘ 「每月**新增**持牌食肆数量」
- ✘ 「特定区域内食肆总数**变化**」

我还试了 data.gov.hk 的历史存档 API 想回溯快照：

```
GET https://api.data.gov.hk/v1/historical-archive/list-file-versions
    ?url=https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML
    &start=20210101&end=20261009
→ 200 OK, {"versions": []}     ← 0 个版本
```
对 AQHI、酒店、流感等 URL 试同样的调用，同样全部返回 0 → **该存档服务对这批资料不可用**。

### 3.3 人口普查 △ 只有一个横截面

75 × 209 的表，只有 2021 年一个时点。放进月度面板里**时间上零变异**，只能当
「时间不变的协变量」（固定效应模型、或与旅游指标的交互项），不能做「随时间的协变量」。

### 3.4 我找到的替代：「食肆活动」的时间序列

data.gov.hk 上有 **C&SD 625-68003「Restaurant receipts by type of restaurant」**（季度）：

```
季度数据 87 期  2004Q4 → 2026Q2
分组：Total / Chinese restaurants / Non-Chinese restaurants / Fast food shops /
      Bars / Miscellaneous eating and drinking places
单位：HK$ million
```

- 这是**食肆营业额**，是「商业活力」的合理代理变量，且**有时间序列**。
- 代价：季度粒度（酒店是月），需要降频；且**只有全港、没有分区**。

### 3.5 拼接实测

我把酒店入住率从月聚合成季，与餐饮收益做内连接：**成功对上 20 个季度**（2021Q3–2026Q2）。

```
酒店(月→季平均) ⋈ 餐饮收益(季)：20 季 × 14 欄
```
输出：`out/f2_joined_hotel_restaurant_quarterly.csv`

### 3.6 建议的改写

| 原设计 | 建议 |
| --- | --- |
| 主数据：酒店入住率（月度，8 旅游区） | **保留** |
| 关联数据：食肆牌照新增数 | ✘ 换成 **C&SD 625-68003 餐饮业收益（季度，全港）** |
| 协变量：2021 普查收入/人口结构 | 保留，但降级为「时间不变协变量」；地理键需自行做 8 旅游区 → 18 区的对照 |
| 粒度 | 统一到**季度**（酒店月→季平均） |
| 额外可加 | **C&SD 650-80001 访港旅客**（月度，271 期，2004-01 起）→ 把因果链补齐为「旅客 → 酒店 → 餐饮」 |

> **结论：方案二可救，但核心数据要从「食肆牌照」换成「餐饮业收益」，粒度降到季度。**

---

## 4. 方案三：公共卫生负担与医疗资源利用 —— ⚠️ 需换结局变量（最接近可行）

**脚本**：`scripts/22_test_f3.py`　**日志**：`out/22_test_f3.log`

### 4.1 流感速递 ✔ 质量很好

```
666 周   2014-01-04 → 2026-10-03   32 个欄位
关键欄位缺失率：
  ILI_PMP               0.0%    定点普通科门诊流感样病例比率
  AandB / H1 / H3 / B   0.0%    实验室监测
  Adm_All               0.0%    整体入院率
  Adm_65_higher         0.0%    65+ 入院率   ← 正好是你想要的年龄组
  SevereCase_65_higher 16.4%    65+ 严重流感个案（只在流感季有值）
  ILI_AED               0.0%    急症室流感样病例比率
```
**周粒度、12 年、字段齐全** —— 这是三个方案里最好的一份资料。

### 4.2 死亡统计 ✘ 缺你需要的切片

逐个查了所有死亡相关表的维度：

| 表 | 频率 | 维度 | 覆盖 |
| --- | --- | --- | --- |
| C&SD 115-01022A 月度死亡（按性别） | **月**（607 期） | **只有 SEX**，无 AGE、无 CAUSE | 1976-01 → 2026-07 |
| C&SD 115-01022 死亡（按性别+年龄组） | **年** | SEX × AGE | 只有年度 |
| C&SD 115-01023 年龄性别死亡率 | 年 | SEX × AGE | 只有年度 |
| DH NCDD 主要死因死亡数 | **年** | 死因（无年龄） | 2001–2024 |
| C&SD 930-92081A 须通报传染病死亡 | 年 | — | — |

**结论：data.gov.hk 上没有「周 × 65 岁及以上 × 呼吸系统疾病」这个切片。**
你的「结局变量」在原设计里不存在：

- 按**周**聚合 → 死亡端没有周数据
- **65 岁及以上** → 月度表没有年龄拆分
- **呼吸系统疾病** → 月度表没有死因拆分，死因表只有年度

### 4.3 但方案三可以救 —— 三条路

**(a) 换成月度建模**（我实测跑通了）

把流感周数据降频到月，与 115-01022A 月度总死亡数对齐：

```
月度死亡 : 607 个月  1976-01 → 2026-07
流感(周→月): 154 个月 2014-01 → 2026-10
内连接   : 151 个月（2014-01 → 2026-07）

建模样本 n = 149
OLS (deaths ~ ILI lags + Adm65 lags):  R² = 0.099
NB-GLM:  deviance = 3   ← 负二项跑得通
相关系数(月死亡数 vs 同月 ILI) = -0.162
```

- 代价：**丢掉周解析度**，且结局只能是「月度总死亡数」。
- 好消息：**计数回归（泊松/负二项）+ 滞后特征 + 变化点检测** 这些课程契合点全部保留。
- 可以做「**超额死亡**」（excess mortality）：用历史月均值做基线，算 2020–2026 的超额部分。

**(b) 换结局变量：用 HA 每日服务量**

[医管局「Key Statistics during Service Demand Surge」](https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge)：

```
HA Overall：928 天  2019-12-01 → 2026-08-04
欄位：ae_first_attend（急症室首次求诊）、ae_to_med_ip（经急症室入院）、
      med_bed_occ_rate（内科病床占用率 %）、ped_bed_occ_rate
← 有「周/日」解析度，还带 8 个联网 / 逐医院拆分
```

与流感周数据可共同覆盖 **134 周**。这直接对应你原题的「医疗系统哪些指标承受最大压力」，
而且**每天都能对齐**。
⚠️ 注意：该数据只覆盖「服务高峰季」（928 天 / 约 6.8 年，不是全年）→ 只能做季节性分析，不能做全年时间序列。

**(c) 把「死亡」换成流感自身的严重个案**
`SevereCase_65_higher`（周，16.4% 缺失，只在流感季有值）可作次要结局。

### 4.4 建议的改写

| 原设计 | 建议 |
| --- | --- |
| 主数据：流感速递（周） | **保留** |
| 结局：周 × 65+ × 呼吸系统疾病死亡 | ✘ 不存在。换成 **(b) HA 每日/每周急症室求诊 + 内科病床占用率**，或 (a) **月度总死亡数/超额死亡** |
| 关联方式 | 时间键对齐完全可行（周↔周 或 周→月降频） |
| 课程契合点 | **完全保留**：时间序列、负二项/泊松回归、变化点检测、模型评估 |

> **结论：方案三最可行。唯一要改的是结局变量 —— 死亡数据在 data.gov.hk 上没有你要的切片。**

---

## 5. 三方案横向对照

| | 方案一 | 方案二 | 方案三 |
| --- | --- | --- | --- |
| 主数据粒度 | 年（3 期）❌ | 月（60 期）✔ | 周（666 期）✔ |
| 关联数据可用性 | AQHI 小时级 ✔ | 食肆牌照无日期 ❌ | 死亡数据缺切片 ❌ |
| 时间键能否对齐 | 差 3 个数量级 ❌ | 月↔季需降频 ⚠️ | 周↔月需降频 ⚠️ |
| 地理键能否对齐 | 路段↔站↔区，无主键 ❌ | 8 旅游区↔18 区 ⚠️ | 无需地理键 ✔ |
| 协变量（普查） | 单年横截面 ⚠️ | 单年横截面 ⚠️ | 不需要 |
| 课程契合度 | 时间序列 ✘（样本=3） | 多源融合 ✔ / 时序 ⚠️ | 时序 + 计数回归 ✔✔ |
| **总评** | **放弃** | **可救（换数据源）** | **推荐（换结局）** |

### 推荐优先级

1. **方案三（改写版）** —— 用「流感周数据 × HA 每日服务量」或「流感周数据 → 月度总死亡/超额死亡」。
   数据结构最干净，课程知识点全覆盖，数据可得性最好。**强烈推荐**。
2. **方案二（改写版）** —— 用「访港旅客 + 酒店入住率 + 餐饮业收益」的月度/季度面板，
   再做地理分层。需要接受「全港层面 + 季度」的限制。
3. **方案一** —— 数据源不支持原设计，建议更换题目方向。

---

## 6. 复现方式

```bash
cd project
export UV_CACHE_DIR=$PWD/.uv-cache

# 环境（已建好）
uv sync

# 下载（203 个文件，约 30 MB）
.venv/bin/python scripts/exploratory/12_download_all.py

# 三个方案的实测
.venv/bin/python scripts/exploratory/20_test_f1.py   # 方案一
.venv/bin/python scripts/exploratory/21_test_f2.py   # 方案二
.venv/bin/python scripts/exploratory/22_test_f3.py   # 方案三
```

### 目录

```
project/
├── REPORT.md              本报告
├── pyproject.toml / uv.lock / .venv    隔离环境
├── data/                  下载的原始数据（30 MB）
│   ├── f1_traffic/  (48 CSV)   f1_aqhi/ (151 CSV)   f1_census/
│   ├── f2_hotel/    f2_licence/  f2_rest/  f2_visitor/
│   └── f3_flu/      f3_death/    f3_ha/
├── scripts/               00–24 探测与实测脚本
└── out/                   实测日志、中间成果 CSV、数据集页面截图
```

### 需要你决定的事

1. **方案一是否放弃？** 我建议放弃或改题（数据源硬限制）。
2. **方案二是否接受「餐饮业收益」替代「食肆牌照」**、并把粒度降到季度？
3. **方案三选哪条结局？**
   - (a) 月度总死亡数 / 超额死亡（时序长，2014–2026）
   - (b) HA 每日急症室 + 病床占用率（周/日对齐，但只覆盖流感高峰季）
   - (c) 两者都做（(a) 做长期趋势，(b) 做高峰季机制）
4. 是否要我把选定方案写成完整的数据管道 + 建模 notebook？
