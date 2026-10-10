# Data Guide

`data/processed/panel_hospital_week.csv` — a weekly panel of emergency-care service
load across Hong Kong public hospitals.

**The short version:** this is a 2,448 × 34 panel — 17 hospitals × 144 weeks. The
time axis is not continuous; it is eight separate winter windows. And none of the
nine influenza variables varies across hospitals. Those three facts decide what
this dataset can and cannot answer, so please read Section 4 before you start
modelling.

> A Chinese version of this guide is available at [`DATA_GUIDE.zh.md`](DATA_GUIDE.zh.md).

---

## 1. Where the data comes from

Six public data sources. Raw files live in `data/raw/` and are never modified —
all cleaning happens in `pipeline/01_build.py`.

**Download links and checksums are in [`data/raw/SOURCES.md`](data/raw/SOURCES.md).**
The machine-readable record is `data/raw/_manifest.json`; the official dataset
metadata is `data/raw/_provenance.json`.

| # | Provider | Dataset | Frequency | Local file | Role |
|---|---|---|---|---|---|
| 1 | Department of Health, CHP | Flu Express figures | Weekly | `flu/flux_data.csv` | **Predictors** |
| 2 | Hospital Authority | Key Statistics during Service Demand Surge | Daily (during surge) | `ha/service_demand_surge_daily.json` | **Response variables** |
| 3 | Hospital Authority | Inpatient and Day Inpatient Services Throughput | Financial year | `ha/hospital_beds.json` | Covariate |
| 4 | Hospital Authority | Ambulatory and Community Services Throughput | Financial year | `ha/ae_attendances_annual.json` | Covariate |
| 5 | Hospital Authority | Hospital / institution list | Quarterly | `ha/facility_hospitals.json` | Geography |
| 6 | Hong Kong Observatory | Open Data API, daily temperature | Daily | `hko/CLM*_YYYY.csv` × 24 | Covariate |

Raw data at a glance:

```
Flu Express           666 weeks     2014-01-04 → 2026-10-03
HA surge statistics   16,704 rows   2019-12-01 → 2026-08-04   (928 distinct dates)
HA hospital beds      807 rows      FY2008-09 → FY2024-25
HA annual A&E         293 rows      FY2008-09 → FY2024-25
HA facility list      44 institutions
HKO daily temperature 2,800 days   2019-01-01 → 2026-08-31
```

The week definition comes from Flu Express: each week ends on the `To` date
(a Saturday). Every other source is aggregated onto that same boundary.

---

## 2. Columns of the main table

The 34 columns fall into six groups:

| Group | Cols | Names |
|---|---|---|
| Identifiers | 6 | `hospital`, `cluster`, `fy`, `season`, `week_start`, `week_end` |
| **Response** | 4 | `ae_first_attend`, `ae_to_med_ip`, `med_bed_occ_rate`, `ped_bed_occ_rate` |
| **Predictors** | 9 | `ILI_PMP`, `ILI_AED`, `Adm_65`, `Adm_All`, `Severe65`, `flu_H1`, `flu_H3`, `flu_B`, `flu_AandB` |
| Hospital covariates | 8 | `beds_acute`, `beds_infirmary`, `beds_mental`, `beds_mh`, `ae_annual`, `with_AE`, `lat`, `lon` |
| Temperature covariates | 3 | `temp_mean`, `temp_max`, `temp_min` |
| Data-quality flags | 4 | `temp_days`, `days`, `week_in_season`, `prev_gap_days` |

A machine-readable dictionary with types, units, non-null counts and missing
rates is at **`data/processed/data_dictionary.csv`**.

---

## 3. Variables in detail

### 3.1 Identifiers

| Column | Meaning |
|---|---|
| `hospital` | Hospital name, 17 values. Names are harmonised across sources (see Section 5) |
| `cluster` | Hospital cluster, 7 values: Hong Kong East / West, Kowloon Central / East / West, New Territories East / West |
| `fy` | Financial year starting 1 April, e.g. `2023-24` |
| `season` | Influenza season label (July boundary), 8 values: `2019-20` … `2026-27` |
| `week_start` / `week_end` | First day (Sunday) and last day (Saturday) of the week |

The 17 hospitals, grouped by cluster:

```
Hong Kong East       (2)  Pamela Youde Nethersole Eastern, Ruttonjee
Hong Kong West       (1)  Queen Mary
Kowloon Central      (2)  Kwong Wah, Queen Elizabeth
Kowloon East         (2)  Tseung Kwan O, United Christian
Kowloon West         (4)  Caritas Medical Centre, North Lantau, Princess Margaret, Yan Chai
New Territories East (3)  Alice Ho Miu Ling Nethersole, North District, Prince of Wales
New Territories West (3)  Pok Oi, Tin Shui Wai, Tuen Mun
```

### 3.2 Response variables

| Column | Meaning | Type | n | Missing | Range | Mean ± SD |
|---|---|---|---|---|---|---|
| `ae_first_attend` | A&E first attendances (daily mean over the week) | Count | **2,448** | 0.00% | 87 – 597 | 290.4 ± 88.9 |
| `ae_to_med_ip` | Admissions to medical wards via A&E (daily mean) | Count | 2,302 | 5.96% | 1 – 124.9 | 59.7 ± 22.9 |
| `med_bed_occ_rate` | Medical bed occupancy (daily mean) | Bounded % | 2,304 | 5.88% | 58 – 138 | 101.8 ± 11.7 |
| `ped_bed_occ_rate` | Paediatric bed occupancy (daily mean) | Bounded % | 1,597 | 34.76% | 10.2 – 128.7 | 66.0 ± 21.3 |

**Distributional choices.** The first two are counts — Poisson or negative
binomial. The last two are proportions — Beta regression, logit-transformed OLS,
or plain OLS with robust standard errors.

**The usable sample differs by response variable**, because it depends on whether
a hospital has the relevant department:

- `ae_first_attend` — all 17 hospitals
- `ae_to_med_ip` and `med_bed_occ_rate` — missing for North Lantau, which has no
  medical inpatient service (100% missing), plus a few gaps for Tin Shui Wai
- `ped_bed_occ_rate` — complete for the **11 hospitals** with a paediatric ward;
  5 hospitals have none at all (North District, Pok Oi, Ruttonjee, Tin Shui Wai,
  North Lantau), and Yan Chai is only 9% covered

> The panel is balanced in shape, but **each model runs on a different subsample**.
> Do not assume one table feeds four models.

### 3.3 Predictors (influenza activity)

| Column | Meaning | Unit | Mean ± SD | Range |
|---|---|---|---|---|
| `ILI_PMP` | Influenza-like illness rate, sentinel general outpatient clinics | per 1,000 consultations | 30.7 ± 15.1 | 5.6 – 77.1 |
| `ILI_AED` | Influenza-like illness rate, A&E departments | per 1,000 consultations | 147.6 ± 50.5 | 65 – 327 |
| `Adm_65` | Influenza admission rate, aged 65+ | per 1,000 population | 0.58 ± 0.73 | 0 – 3.10 |
| `Adm_All` | Influenza admission rate, all ages | per 1,000 population | 0.26 ± 0.31 | 0 – 1.22 |
| `Severe65` | Severe influenza cases, aged 65+ | cases per week | 12.7 ± 15.6 | 0 – 68 |
| `flu_H1`, `flu_H3`, `flu_B` | Laboratory-confirmed influenza, by type | cases per week | 212.2 / 98.8 / 29.3 | — |
| `flu_AandB` | Laboratory-confirmed influenza A + B | cases per week | 351.5 ± 427.2 | 0 – 2,015 |

All nine are **fully observed** — no missing values.

### 3.4 Hospital covariates

| Column | Meaning | Mean | Range | Coverage |
|---|---|---|---|---|
| `beds_acute` | Acute and convalescent beds | 1,118 | 130 – 2,110 | 100% |
| `beds_infirmary` | Infirmary beds | — | — | 100% |
| `beds_mental` | Mentally ill beds | — | — | 100% |
| `beds_mh` | Mentally handicapped beds | — | — | 100% |
| `ae_annual` | Total A&E attendances in that financial year | 113,203 | 51,825 – 199,427 | 100% |
| `with_AE` | Whether the institution runs an A&E | — | all Yes | 100% |
| `lat`, `lon` | Hospital coordinates | — | — | 100% |

`beds_*` and `ae_annual` are published **annually**, and only up to FY2024-25.
Later weeks carry the last published year forward — bed counts are slow-moving
(year-on-year change below 2%).

FY2023-24 sizes for the six largest hospitals:

```
Tuen Mun Hospital                2,081 acute beds   173,819 annual A&E attendances
Queen Elizabeth Hospital         2,018 acute beds   199,427 annual A&E attendances
Prince of Wales Hospital         1,901 acute beds   166,509 annual A&E attendances
Princess Margaret Hospital       1,680 acute beds   117,378 annual A&E attendances
Queen Mary Hospital              1,557 acute beds   117,148 annual A&E attendances
Pamela Youde Nethersole Eastern  1,529 acute beds   118,898 annual A&E attendances
```

### 3.5 Temperature covariates

`temp_mean`, `temp_max`, `temp_min` — weekly means of daily readings at the Hong
Kong Observatory headquarters, in °C. `temp_mean` spans 12.1 – 30.1, fully observed.

### 3.6 Data-quality columns — read these before modelling

| Column | Meaning | Values |
|---|---|---|
| `days` | How many days of HA data the week actually contains | 1–7. `== 7` for 2,108 rows, `< 7` for 340 |
| `week_in_season` | Index of the week within its season | 1, 2, 3, … (contiguous) |
| `prev_gap_days` | Days since the previous published week in the same season | `0` (first week of a season) / `7` (normal) / `> 7` (HA gap; 68 rows) |
| `temp_days` | Days with a temperature reading in that week | always 7 |

---

## 4. Three structural facts you must know

### 4.1 The predictors have no cross-sectional variation

All nine influenza variables are a **single territory-wide time series** — every
hospital gets the identical value in a given week.

```
week_end       2019-12-07  2019-12-14  2019-12-21  2019-12-28
North Lantau         16.2        26.4        28.0        29.1
Queen Mary           16.2        26.4        28.0        29.1
Tuen Mun             16.2        26.4        28.0        29.1
                     ↑ identical
```

**What follows:**

- They can only explain territory-wide week-to-week movement. They **cannot**
  explain why hospital A is busier than hospital B.
- They cannot be interacted with hospital fixed effects to identify
  hospital-level time-varying effects.
- Cross-hospital differences have to come from hospital fixed effects and the
  capacity covariates (`beds_acute`, `ae_annual`, and so on).

### 4.2 The time axis is discontinuous — eight winter windows

`T = 144` is not 144 consecutive weeks. It is eight separate windows:

```
season    weeks   first        last         gaps
2019-20      13   2019-12-07   2020-02-29   none
2020-21      22   2020-12-05   2021-05-01   none
2021-22      22   2021-12-04   2022-04-30   none
2022-23      30   2022-12-03   2023-06-24   none
2023-24      26   2023-12-23   2024-06-22   1 gap (14 days)
2024-25      17   2024-12-21   2025-05-10   1 gap (35 days)
2025-26      11   2025-12-27   2026-04-11   2 gaps (21 and 28 days)
2026-27       3   2026-07-25   2026-08-08   none
```

**What follows:**

- You cannot treat this as a continuous time series. ARIMA and full-year STL
  decomposition do not apply.
- You cannot run `shift(1)` on the whole table to build lags.
- Stratify by `season` and treat each winter as a separate surge episode.

> **When you build lagged variables:**
> ```python
> df = df.sort_values(["season", "week_end"])
> df["ili_lag1"] = df.groupby("season")["ILI_PMP"].shift(1)
> # and mask the ones that cross a gap:
> df.loc[df["prev_gap_days"] > 7, "ili_lag1"] = np.nan
> ```
> Without this, the four gaps will silently give you a value from several weeks
> earlier, labelled as "last week".

### 4.3 Some weeks are incomplete

For the 340 rows with `days < 7`, the weekly mean is computed from fewer than
seven days — sometimes only one, so it is noisier.

Options:
- (a) keep everything and weight by `days`
- (b) keep only `days == 7` (2,108 rows)
- (c) keep everything, and use (b) as a robustness check ← **recommended**

---

## 5. Traps already handled in the pipeline

These came up while building the table. **If you merge from `data/raw/` yourself,
handle them the same way.**

**① Hospital names differ across sources.** The HA publishes the same hospital
under different names:

```
Surge statistics:            Ruttonjee & Tang Shiu Kin Hospitals
Bed table (pre-2017-18):     Ruttonjee Hospital
Bed table (2017-18 onward):  Ruttonjee & Tang Shiu Kin Hospitals
Annual A&E / facility list:  Ruttonjee Hospital
```

Unharmonised, the hospital **disappears silently** — the merge produces NaN
rather than an error. The mapping lives in `HOSPITAL_NAME_MAP` in
`pipeline/01_build.py`.

**② The facility list groups clusters differently.** It merges Hong Kong Island
into one cluster, while the surge statistics split it into Hong Kong East and
Hong Kong West. The facility list is used only for coordinates.

**③ The facility list has 18 A&E hospitals; the surge data covers 17.** The
missing one is **St. John Hospital** (Cheung Chau, very small).

**④ The bed table includes an "Overall" specialty row.** It must be dropped or
beds get double-counted.

**⑤ The annual A&E table includes cluster-level "Overall (...)" rows.** Same
treatment.

**⑥ The HA stopped publishing for some weeks from 2023-24 onward.** This produces
the gaps in Section 4.2, flagged by `prev_gap_days`.

---

## 6. Signals already visible — a starting point

Before modelling, it is worth confirming these relationships exist.

**Territory-wide, weekly (n = 144):**

```
A&E first attendances   vs ILI_PMP   r = +0.695
Admissions via A&E      vs ILI_PMP   r = +0.639
Medical bed occupancy   vs ILI_PMP   r = +0.575
```

**Per hospital, A&E first attendances vs ILI_PMP (n = 144 each) — the spread is wide:**

```
+0.802  Kwong Wah Hospital                    <- most responsive
+0.742  Tuen Mun Hospital
+0.735  Queen Elizabeth Hospital
+0.724  North District Hospital
+0.698  Tseung Kwan O Hospital
+0.690  Prince of Wales Hospital
+0.687  Ruttonjee Hospital
+0.669  United Christian Hospital
+0.664  Yan Chai Hospital
+0.656  Pok Oi Hospital
+0.617  Queen Mary Hospital
+0.582  Alice Ho Miu Ling Nethersole Hospital
+0.576  North Lantau Hospital
+0.573  Pamela Youde Nethersole Eastern Hospital
+0.569  Princess Margaret Hospital
+0.508  Tin Shui Wai Hospital
+0.449  Caritas Medical Centre                <- least responsive
```

**Territory-wide by season (HA Overall):**

```
season    weeks   A&E mean   A&E peak   occupancy mean   occupancy peak
2019-20      13      4,880      5,920             98.9            113.4
2020-21      22      4,337      5,090             97.8            104.4
2021-22      22      4,091      5,111             96.0            105.0
2022-23      30      5,286      6,287            105.6            116.4
2023-24      26      5,581      5,988            106.9            114.0
2024-25      17      5,305      5,633            105.1            110.4
2025-26      11      4,761      5,084            102.2            106.2
2026-27       3      5,235      5,366            109.4            110.7
```

Medical bed occupancy **exceeds 100% in almost every season** — the system runs
over capacity, peaking at 116%. Levels were visibly lower during COVID
(2020-21, 2021-22) and rebounded from 2022-23 onward. That pattern is itself
worth analysing.

---

## 7. What you can and cannot do

### 7.1 Questions this dataset can answer

With the unit of analysis as `(hospital i, week t)`:

**① Dose–response and lag structure**

$$\log \mathbb{E}[Y_{it}] = \alpha_i + \delta_{s(it)} + \sum_{k=0}^{K} \beta_k X_{t-k} + \mathbf{Z}_i^\top \gamma$$

How much does emergency-care load rise per unit of influenza activity, and how
many weeks does the peak lag behind?

**② Hospital heterogeneity**

$$\text{occupancy}_{it} = \alpha_i + \delta_s + \beta X_t + \theta (X_t \times Z_i) + \varepsilon_{it}$$

Which hospitals respond most strongly, and is their vulnerability driven by a
high baseline load or by high responsiveness? The correlation spread in
Section 6 (0.449 to 0.802) suggests there is real variation to explain.

**③ Non-linearity and thresholds**

At what level of influenza activity does medical bed occupancy cross 100%, and
does deterioration accelerate beyond it? Threshold regression (Hansen), splines
or GAMs, and change-point detection all apply.

**④ Comparison across seasons**

Using 2022-23 — the first complete post-COVID influenza season — as a break
point, test whether the transmission from influenza to load has changed.

### 7.2 Suggested methods and robustness checks

| Purpose | Method |
|---|---|
| Count responses | Poisson / negative binomial GLM with a log link |
| Proportion responses | Beta regression or logit-transformed OLS |
| Panel structure | Two-way fixed effects (hospital + season), standard errors clustered by hospital |
| Lag structure | Unrestricted lags 0–3 with a joint Wald test |
| Non-linearity | GAM or piecewise regression to locate a threshold |
| Validation | Leave-one-season-out cross-validation; off-season placebo test |

**Robustness checklist:**

1. Restrict to complete weeks (`days == 7`, 2,108 rows)
2. Rotate the predictor: `ILI_PMP` ↔ `Adm_65` ↔ `flu_AandB`
3. Change the spatial unit: hospital level ↔ cluster level (7 units, less noise)
4. Drop the COVID seasons (2020-21, 2021-22) and re-estimate
5. Placebo: use off-season months (July–October) and check the association disappears
6. Multiple comparisons: Benjamini–Hochberg FDR

### 7.3 Questions this dataset cannot answer

| Tempting but not supported | Why not |
|---|---|
| Individual-level causal inference | The influenza series is a **territory-wide ecological indicator**, not a hospital-catchment measure |
| Mortality outcomes | Government monthly deaths carry **no age or cause breakdown**; age detail exists only annually |
| Daily or intra-day modelling | The exposure is weekly |
| Full-year time series | The axis has four gaps and only eight winter windows |
| Within-hospital time-varying effects | The predictors have no cross-sectional variation (Section 4.1) |
| A&E waiting time as an outcome | HA publishes waiting time as a **live snapshot** with no date field, so it is not a time series |
| Long-run trends or annual analysis | Coverage starts in December 2019, with seven winters |

---

## 8. FAQ

**Is `T = 144` 144 consecutive weeks?**
No. It is the total number of weeks across eight winter windows, with four gaps
in between. See Section 4.2.

**Why can `med_bed_occ_rate` exceed 100%?**
Occupancy is inpatients divided by beds. When beds are added in corridors or
temporary spaces, the numerator exceeds the denominator.

**`ped_bed_occ_rate` is heavily missing — what should I do?**
Build a separate sub-panel of the 11 hospitals with a paediatric ward. Do not use
it in the main model; you would lose six hospitals.

**Should I drop North Lantau because it has no medical data?**
Keep it for models using `ae_first_attend`, where it is fully observed. For
medical outcomes it drops out automatically via `dropna`.

**Is `beds_acute` constant within a season?**
It is constant within a financial year, and changes once a year in April. In a
fixed-effects model, hospital fixed effects will absorb most of its variation.

**Can I add more sources?**
Yes. Relative humidity is available from the same HKO API (the parameter code
needs checking). On the transport side, monthly public transport patronage from
`hk-td-tis_17` can be aligned to these weeks or months.

---

## 9. Merging the data yourself

To work from `data/raw/` rather than the finished tables:

```bash
# See how the pipeline does it
cat pipeline/01_build.py

# pandas is all you need; the key steps are S1-S6, and the
# processing conventions sit in the constants block at the top of the file
```

The pipeline writes six tables:

| File | Size | Contents |
|---|---|---|
| `panel_hospital_week.csv` | 2,448 × 34 | **Main analysis table** |
| `hk_weekly.csv` | 144 × 23 | Territory-wide weekly series (HA Overall) |
| `hospital_beds_annual.csv` | hospital × FY | Bed counts, wide format (FY2008-09 onward) |
| `ae_attendances_annual.csv` | hospital × FY | Annual A&E attendances (FY2008-09 onward) |
| `hospital_directory.csv` | 44 institutions | Names, clusters, A&E flag, address, coordinates |
| `data_dictionary.csv` | 34 rows | Variable dictionary |

Rebuilding and comparing against `data/processed/` is a good way to check your
understanding — the pipeline is deterministic, so the output should match byte
for byte.

---

## 10. Known limitations

1. **Discontinuous time axis** — eight winter windows, not a continuous series
2. **Ecological exposure** — a territory-wide indicator, so no individual-level inference
3. **COVID confounding** — 2020–2022 saw mask mandates and distancing that suppressed both influenza and A&E demand simultaneously
4. **No mortality stratification** — monthly deaths carry no age or cause detail
5. **Annual bed counts** — within-year capacity changes are not observable
6. **Only seven influenza seasons** — a small sample for season-level inference
