# 原始数据来源与下载链接

本目录下的原始文件**全部来自公开数据源**，可按下表从官网手动下载。
下载后保持左侧的文件路径不变即可，管道（`pipeline/`）会直接从本目录读取。

> 本文件由 `data/raw/_manifest.json` 生成，记录了每个文件的 URL 与 SHA256。
> 机器可读版本见 `_manifest.json`；data.gov.hk 数据集官方元数据见 `_provenance.json`。

共 29 个文件。抓取时间：2026-10-10T15:45:34+00:00

## 数据集官方页面

| 数据集 | 提供机构 | 更新频率 | 页面 |
|---|---|---|---|
| Flu Express's figures data | Department of Health | Weekly | <https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express> |
| Key Statistics during Service Demand Surge | Hospital Authority | Daily (during surge period) | <https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge> |
| Inpatient and Day Inpatient Services Throughput | Hospital Authority | Annually | <https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ipdp> |
| Ambulatory and Community Services Throughput | Hospital Authority | Annually | <https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ambulatory-community> |
| List of Hospital Authority Hospitals/Institutions/Specialist Outpatient Clinics/Family Medicine Clinics | Hospital Authority | Quarterly (January, April, July and October) | <https://data.gov.hk/sc-data/dataset/hospital-hadata-health-care-facilities> |

## 逐文件下载链接

### 流感监测（卫生署 卫生防护中心）

数据集页面：<https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express>

| 本地文件 | 下载链接 | SHA256（前 16 位） |
|---|---|---|
| `flu/flux_data.csv` | <https://www.chp.gov.hk/files/misc/flux_data.csv> | `a59f57ea0a920d8c…` |

### 医院管理局

数据集页面：<https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge>

| 本地文件 | 下载链接 | SHA256（前 16 位） |
|---|---|---|
| `ha/ae_attendances_annual.json` | <https://www.ha.org.hk/opendata/ae-attnd-en.json> | `5faa9c7c588f8802…` |
| `ha/facility_hospitals.json` | <https://www.ha.org.hk/opendata/facility-hosp.json> | `02a01027c1879f1b…` |
| `ha/hospital_beds.json` | <https://www.ha.org.hk/opendata/hosp-bed-en.json> | `42dd2d061c793a60…` |
| `ha/service_demand_surge_daily.json` | <https://www.ha.org.hk/opendata/pas_report/Daily_Services_Statistics/Daily_Services_Statistics_EN.json> | `75189ca5a7e32025…` |

### 香港天文台（逐日气温）

接口：`https://data.weather.gov.hk/weatherAPI/opendata/opendata.php`
参数：`dataType` ∈ {CLMTEMP 日均, CLMMAXT 日最高, CLMMINT 日最低}，`lang=en`，`rformat=csv`，`year=2019..2026`，`station=HKO`

| 本地文件 | 完整 URL | SHA256（前 16 位） |
|---|---|---|
| `hko/CLMMAXT_2019.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2019&station=HKO> | `ad636c124d39721b…` |
| `hko/CLMMAXT_2020.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2020&station=HKO> | `6d985547c8454192…` |
| `hko/CLMMAXT_2021.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2021&station=HKO> | `77ae52ec01705e31…` |
| `hko/CLMMAXT_2022.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2022&station=HKO> | `5365ce5496bb507b…` |
| `hko/CLMMAXT_2023.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2023&station=HKO> | `d20c9fb0088d2699…` |
| `hko/CLMMAXT_2024.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2024&station=HKO> | `8766f3ef865797c2…` |
| `hko/CLMMAXT_2025.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2025&station=HKO> | `991e404094ae6b71…` |
| `hko/CLMMAXT_2026.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2026&station=HKO> | `4c64bc82b0484e9f…` |
| `hko/CLMMINT_2019.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2019&station=HKO> | `47562cdeef8d9eb9…` |
| `hko/CLMMINT_2020.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2020&station=HKO> | `411b8691d5dcc01f…` |
| `hko/CLMMINT_2021.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2021&station=HKO> | `953c35a90212e9d4…` |
| `hko/CLMMINT_2022.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2022&station=HKO> | `af4b35db1be9b6fd…` |
| `hko/CLMMINT_2023.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2023&station=HKO> | `6ef582b718cc3fe6…` |
| `hko/CLMMINT_2024.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2024&station=HKO> | `42fb7d5d0ee3b9be…` |
| `hko/CLMMINT_2025.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2025&station=HKO> | `e2cabef880eae9a2…` |
| `hko/CLMMINT_2026.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2026&station=HKO> | `db62142c09a6f3bd…` |
| `hko/CLMTEMP_2019.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2019&station=HKO> | `733afc696d0dc82b…` |
| `hko/CLMTEMP_2020.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2020&station=HKO> | `202fae5f2f3d16d3…` |
| `hko/CLMTEMP_2021.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2021&station=HKO> | `456421fe7ce8ab35…` |
| `hko/CLMTEMP_2022.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2022&station=HKO> | `a0ac063acdac7ae9…` |
| `hko/CLMTEMP_2023.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2023&station=HKO> | `45de3d34bf4c8408…` |
| `hko/CLMTEMP_2024.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2024&station=HKO> | `1f985243efa37f54…` |
| `hko/CLMTEMP_2025.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2025&station=HKO> | `3f3eedc82f799ea6…` |
| `hko/CLMTEMP_2026.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2026&station=HKO> | `872d3a516e069415…` |

## 文件清单汇总

| 本地文件 | 用途 | 字节数 |
|---|---|---|
| `flu/flux_data.csv` | 解释变量（周） | 96,295 |
| `ha/ae_attendances_annual.json` | 协变量：急症室年服务量 | 67,543 |
| `ha/facility_hospitals.json` | 空间维度：联网归属与坐标 | 25,974 |
| `ha/hospital_beds.json` | 协变量：病床数（财政年度） | 453,129 |
| `ha/service_demand_surge_daily.json` | 结果变量（日 × 医院） | 4,333,741 |
| `hko/CLMMAXT_2019.csv` | 协变量：逐日气温 | 6,473 |
| `hko/CLMMAXT_2020.csv` | 协变量：逐日气温 | 6,490 |
| `hko/CLMMAXT_2021.csv` | 协变量：逐日气温 | 6,473 |
| `hko/CLMMAXT_2022.csv` | 协变量：逐日气温 | 6,472 |
| `hko/CLMMAXT_2023.csv` | 协变量：逐日气温 | 6,473 |
| `hko/CLMMAXT_2024.csv` | 协变量：逐日气温 | 6,490 |
| `hko/CLMMAXT_2025.csv` | 协变量：逐日气温 | 6,473 |
| `hko/CLMMAXT_2026.csv` | 协变量：逐日气温 | 4,343 |
| `hko/CLMMINT_2019.csv` | 协变量：逐日气温 | 6,473 |
| `hko/CLMMINT_2020.csv` | 协变量：逐日气温 | 6,489 |
| `hko/CLMMINT_2021.csv` | 协变量：逐日气温 | 6,467 |
| `hko/CLMMINT_2022.csv` | 协变量：逐日气温 | 6,467 |
| `hko/CLMMINT_2023.csv` | 协变量：逐日气温 | 6,469 |
| `hko/CLMMINT_2024.csv` | 协变量：逐日气温 | 6,485 |
| `hko/CLMMINT_2025.csv` | 协变量：逐日气温 | 6,473 |
| `hko/CLMMINT_2026.csv` | 协变量：逐日气温 | 4,343 |
| `hko/CLMTEMP_2019.csv` | 协变量：逐日气温 | 6,470 |
| `hko/CLMTEMP_2020.csv` | 协变量：逐日气温 | 6,487 |
| `hko/CLMTEMP_2021.csv` | 协变量：逐日气温 | 6,469 |
| `hko/CLMTEMP_2022.csv` | 协变量：逐日气温 | 6,468 |
| `hko/CLMTEMP_2023.csv` | 协变量：逐日气温 | 6,470 |
| `hko/CLMTEMP_2024.csv` | 协变量：逐日气温 | 6,485 |
| `hko/CLMTEMP_2025.csv` | 协变量：逐日气温 | 6,470 |
| `hko/CLMTEMP_2026.csv` | 协变量：逐日气温 | 4,340 |

## 校验

管道在构建前会自动比对本地文件与 `_manifest.json` 中的 SHA256，
不一致或缺失会给出提示（不中断，因为你可能下载到了更新的版本）。

手动校验单个文件：

```bash
# macOS / Linux
shasum -a 256 data/raw/flu/flux_data.csv
```