# Raw Data Sources

Every file in this directory comes from a public source and can be downloaded
by hand from the links below. Keep the local paths on the left unchanged —
`pipeline/01_build.py` reads this directory directly.

The machine-readable record of the same information is `_manifest.json`
(URL, byte size, SHA256, retrieval time per file). Official dataset metadata
from data.gov.hk is archived in `_provenance.json`.

29 files in total. Retrieved: 2026-10-10T15:45:34+00:00

## Official dataset pages

| Dataset | Provider | Update frequency | Page |
|---|---|---|---|
| Flu Express's figures data | Department of Health | Weekly | <https://data.gov.hk/sc-data/dataset/hk-dh-chpsebcddr-flu-express> |
| Key Statistics during Service Demand Surge | Hospital Authority | Daily (during surge period) | <https://data.gov.hk/sc-data/dataset/hospital-hadata-key-statistics-during-surge> |
| Inpatient and Day Inpatient Services Throughput | Hospital Authority | Annually | <https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ipdp> |
| Ambulatory and Community Services Throughput | Hospital Authority | Annually | <https://data.gov.hk/sc-data/dataset/hospital-hadata-service-ambulatory-community> |
| List of Hospital Authority Hospitals/Institutions/Specialist Outpatient Clinics/Family Medicine Clinics | Hospital Authority | Quarterly (January, April, July and October) | <https://data.gov.hk/sc-data/dataset/hospital-hadata-health-care-facilities> |

## Download links by file

### Influenza surveillance (Department of Health, CHP)

| Local file | URL | SHA256 (first 16) |
|---|---|---|
| `flu/flux_data.csv` | <https://www.chp.gov.hk/files/misc/flux_data.csv> | `a59f57ea0a920d8c...` |

### Hospital Authority

| Local file | URL | SHA256 (first 16) |
|---|---|---|
| `ha/ae_attendances_annual.json` | <https://www.ha.org.hk/opendata/ae-attnd-en.json> | `5faa9c7c588f8802...` |
| `ha/facility_hospitals.json` | <https://www.ha.org.hk/opendata/facility-hosp.json> | `02a01027c1879f1b...` |
| `ha/hospital_beds.json` | <https://www.ha.org.hk/opendata/hosp-bed-en.json> | `42dd2d061c793a60...` |
| `ha/service_demand_surge_daily.json` | <https://www.ha.org.hk/opendata/pas_report/Daily_Services_Statistics/Daily_Services_Statistics_EN.json> | `75189ca5a7e32025...` |

### Hong Kong Observatory (daily temperature)

Endpoint: `https://data.weather.gov.hk/weatherAPI/opendata/opendata.php`

Parameters: `dataType` in {`CLMTEMP` daily mean, `CLMMAXT` daily maximum,
`CLMMINT` daily minimum}, `lang=en`, `rformat=csv`, `year=2019..2026`,
`station=HKO`.

| Local file | URL | SHA256 (first 16) |
|---|---|---|
| `hko/CLMMAXT_2019.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2019&station=HKO> | `ad636c124d39721b...` |
| `hko/CLMMAXT_2020.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2020&station=HKO> | `6d985547c8454192...` |
| `hko/CLMMAXT_2021.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2021&station=HKO> | `77ae52ec01705e31...` |
| `hko/CLMMAXT_2022.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2022&station=HKO> | `5365ce5496bb507b...` |
| `hko/CLMMAXT_2023.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2023&station=HKO> | `d20c9fb0088d2699...` |
| `hko/CLMMAXT_2024.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2024&station=HKO> | `8766f3ef865797c2...` |
| `hko/CLMMAXT_2025.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2025&station=HKO> | `991e404094ae6b71...` |
| `hko/CLMMAXT_2026.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMAXT&lang=en&rformat=csv&year=2026&station=HKO> | `4c64bc82b0484e9f...` |
| `hko/CLMMINT_2019.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2019&station=HKO> | `47562cdeef8d9eb9...` |
| `hko/CLMMINT_2020.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2020&station=HKO> | `411b8691d5dcc01f...` |
| `hko/CLMMINT_2021.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2021&station=HKO> | `953c35a90212e9d4...` |
| `hko/CLMMINT_2022.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2022&station=HKO> | `af4b35db1be9b6fd...` |
| `hko/CLMMINT_2023.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2023&station=HKO> | `6ef582b718cc3fe6...` |
| `hko/CLMMINT_2024.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2024&station=HKO> | `42fb7d5d0ee3b9be...` |
| `hko/CLMMINT_2025.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2025&station=HKO> | `e2cabef880eae9a2...` |
| `hko/CLMMINT_2026.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMMINT&lang=en&rformat=csv&year=2026&station=HKO> | `db62142c09a6f3bd...` |
| `hko/CLMTEMP_2019.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2019&station=HKO> | `733afc696d0dc82b...` |
| `hko/CLMTEMP_2020.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2020&station=HKO> | `202fae5f2f3d16d3...` |
| `hko/CLMTEMP_2021.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2021&station=HKO> | `456421fe7ce8ab35...` |
| `hko/CLMTEMP_2022.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2022&station=HKO> | `a0ac063acdac7ae9...` |
| `hko/CLMTEMP_2023.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2023&station=HKO> | `45de3d34bf4c8408...` |
| `hko/CLMTEMP_2024.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2024&station=HKO> | `1f985243efa37f54...` |
| `hko/CLMTEMP_2025.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2025&station=HKO> | `3f3eedc82f799ea6...` |
| `hko/CLMTEMP_2026.csv` | <https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=CLMTEMP&lang=en&rformat=csv&year=2026&station=HKO> | `872d3a516e069415...` |

## File inventory

| Local file | Role | Bytes |
|---|---|---|
| `flu/flux_data.csv` | Predictors (weekly) | 96,295 |
| `ha/ae_attendances_annual.json` | Covariate: annual A&E attendances | 67,543 |
| `ha/facility_hospitals.json` | Geography: cluster membership and coordinates | 25,974 |
| `ha/hospital_beds.json` | Covariate: bed counts (annual) | 453,129 |
| `ha/service_demand_surge_daily.json` | Response variables (daily x hospital) | 4,333,741 |
| `hko/CLMMAXT_2019.csv` | None | 6,473 |
| `hko/CLMMAXT_2020.csv` | None | 6,490 |
| `hko/CLMMAXT_2021.csv` | None | 6,473 |
| `hko/CLMMAXT_2022.csv` | None | 6,472 |
| `hko/CLMMAXT_2023.csv` | None | 6,473 |
| `hko/CLMMAXT_2024.csv` | None | 6,490 |
| `hko/CLMMAXT_2025.csv` | None | 6,473 |
| `hko/CLMMAXT_2026.csv` | None | 4,343 |
| `hko/CLMMINT_2019.csv` | None | 6,473 |
| `hko/CLMMINT_2020.csv` | None | 6,489 |
| `hko/CLMMINT_2021.csv` | None | 6,467 |
| `hko/CLMMINT_2022.csv` | None | 6,467 |
| `hko/CLMMINT_2023.csv` | None | 6,469 |
| `hko/CLMMINT_2024.csv` | None | 6,485 |
| `hko/CLMMINT_2025.csv` | None | 6,473 |
| `hko/CLMMINT_2026.csv` | None | 4,343 |
| `hko/CLMTEMP_2019.csv` | None | 6,470 |
| `hko/CLMTEMP_2020.csv` | None | 6,487 |
| `hko/CLMTEMP_2021.csv` | None | 6,469 |
| `hko/CLMTEMP_2022.csv` | None | 6,468 |
| `hko/CLMTEMP_2023.csv` | None | 6,470 |
| `hko/CLMTEMP_2024.csv` | None | 6,485 |
| `hko/CLMTEMP_2025.csv` | None | 6,470 |
| `hko/CLMTEMP_2026.csv` | None | 4,340 |

## Verification

Before building, the pipeline compares every local file against the SHA256 in
`_manifest.json` and reports any that are missing or altered. This is advisory
only — it will not stop the build, since you may have downloaded a newer
official release.

To check a file by hand:

```bash
shasum -a 256 data/raw/flu/flux_data.csv
```