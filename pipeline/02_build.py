#!/usr/bin/env python3
"""
02_build.py — 把 data/raw/ 的原始文件清洗、聚合、合并成分析用面板数据。

产出（data/processed/）：
    panel_hospital_week.csv    主分析表：17 医院 × 144 周 = 2,448 行 × 31 列
    hk_weekly.csv              全港周序列（HA Overall）：144 行
    hospital_beds_annual.csv   医院 × 财政年度 病床数
    ae_attendances_annual.csv  医院 × 财政年度 急症室年服务量
    hospital_directory.csv     医院名录、联网、坐标
    data_dictionary.csv        逐列变量字典

处理步骤：
    S1  读入并解析 5 个原始文件
    S2  统一医院/联网名称（跨来源对照）
    S3  HA 逐日数据 → 按流感周界（周日至周六）聚合成周
    S4  医院年度容量协变量（财政年度）并对齐到周
    S5  香港天文台逐日气温 → 聚合成同一边界的周
    S6  合并成主表，写出所有产出

约定：
    * 周的定义一律采用「流感速递」的 From/To；To 为该周最后一天（周六）。
      所有其它来源都对齐到这个边界，以保证跨来源可比。
    * 所有聚合均为确定性运算，不含随机成分。
    * 若 data/raw/ 缺少文件，本脚本会提示先执行 01_download.py。

用法：
    python pipeline/02_build.py
    python pipeline/02_build.py --raw-dir data/raw --out-dir data/processed
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# 常量：处理规则集中在此，便于审阅与修改
# --------------------------------------------------------------------------

# 结果变量（HA 服务需求高峰统计数字）
OUTCOME_COLS = [
    "ae_first_attend",   # 急症室首次求诊人次 / 日
    "ae_to_med_ip",      # 经急症室转入内科住院人次 / 日
    "med_bed_occ_rate",  # 内科病床占用率 %
    "ped_bed_occ_rate",  # 儿科病床占用率 %
]

# 流感暴露变量：源文件列名 -> 输出列名
FLU_COLS = {
    "ILI_PMP": "ILI_PMP",                          # 定点普通科门诊流感样病例比率（主解释变量）
    "ILI_AED": "ILI_AED",                          # 急症室流感样病例比率
    "Adm_65_higher": "Adm_65",                     # 65 岁及以上流感入院率
    "Adm_All": "Adm_All",                          # 整体流感入院率
    "SevereCase_65_higher": "Severe65",            # 65 岁及以上严重流感个案
    "H1": "flu_H1",                                # 实验室确诊甲型 H1
    "H3": "flu_H3",                                # 实验室确诊甲型 H3
    "B": "flu_B",                                  # 实验室确诊乙型
    "AandB": "flu_AandB",                          # 实验室确诊甲型+乙型合计
}

# 跨来源医院名称统一表。
# HA 各部会用不同名称指同一家医院，必须显式对照，否则 merge 会静默丢行。
HOSPITAL_NAME_MAP = {
    "Ruttonjee & Tang Shiu Kin Hospitals": "Ruttonjee Hospital",
}

# HA 设施名录把港岛合并为一个联网，而高峰统计拆成东/西，故只保留名录中的坐标用途。
CLUSTER_NAME_MAP = {
    "Hong Kong Island Cluster": "Hong Kong East/West",
}

# 病床专科 -> 输出列名
BED_SPECIALTY_MAP = {
    "General (Acute and Convalescent)": "beds_acute",
    "Infirmary": "beds_infirmary",
    "Mentally Ill": "beds_mental",
    "Mentally Handicapped": "beds_mh",
}

HKO_DATA_TYPES = {"CLMTEMP": "temp_mean", "CLMMAXT": "temp_max", "CLMMINT": "temp_min"}
HKO_YEARS = list(range(2019, 2027))


# --------------------------------------------------------------------------
# 辅助函数
# --------------------------------------------------------------------------
def fiscal_year(date_like) -> str:
    """日期 -> 香港财政年度字符串（4 月 1 日起算），如 2023-11-01 -> '2023-24'。"""
    ts = pd.Timestamp(date_like)
    y = ts.year if ts.month >= 4 else ts.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def season_label(week_end: pd.Timestamp) -> str:
    """周结束日 -> 流感季标签（7 月为界），如 2020-01-04 -> '2019-20'。"""
    y = week_end.year - 1 if week_end.month < 7 else week_end.year
    return f"{y}-{str(y + 1)[2:]}"


def require(path: pathlib.Path) -> pathlib.Path:
    if not path.exists():
        raise SystemExit(
            f"缺少原始文件：{path}\n请先执行：python pipeline/01_download.py"
        )
    return path


# --------------------------------------------------------------------------
# S1 + S2  读取与名称统一
# --------------------------------------------------------------------------
def load_flu(raw: pathlib.Path) -> pd.DataFrame:
    """流感速递：周粒度，本研究的基准时间轴。"""
    df = pd.read_csv(require(raw / "flu/flux_data.csv"))
    df["week_end"] = pd.to_datetime(df["To"], format="%d/%m/%Y", errors="coerce")
    n_bad = int(df["week_end"].isna().sum())
    df = df.dropna(subset=["week_end"]).copy()
    df["week_start"] = df["week_end"] - pd.Timedelta(days=6)
    df["season"] = df["week_end"].map(season_label)
    df = df.sort_values("week_end").reset_index(drop=True)

    keep = ["week_start", "week_end", "season", "Year", "Week", "From", "To"] + list(FLU_COLS)
    df = df[keep].rename(columns=FLU_COLS)
    df = df.rename(columns={"Year": "flu_year", "Week": "flu_week"})
    df.attrs["n_unparsable_dates"] = n_bad
    return df


def load_surge(raw: pathlib.Path) -> pd.DataFrame:
    """HA 服务需求高峰统计数字：逐日 × 医院。"""
    records = json.loads(require(raw / "ha/service_demand_surge_daily.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    # 全港汇总行的 hospital 字段为空字符串，显式命名，避免与真实医院混淆
    df["hospital"] = df["hospital"].replace("", "HA Overall")
    df["hospital"] = df["hospital"].replace(HOSPITAL_NAME_MAP)
    return df.sort_values(["date", "cluster", "hospital"]).reset_index(drop=True)


def load_beds(raw: pathlib.Path) -> pd.DataFrame:
    """HA 病床数目：财政年度 × 联网 × 医院 × 专科（长表）。"""
    records = json.loads(require(raw / "ha/hospital_beds.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df = df[df["Specialty"] != "Overall"]           # 去掉专科汇总行，避免重复计数
    df["hospital"] = df["Hospital"].replace(HOSPITAL_NAME_MAP)

    wide = (
        df.pivot_table(
            index=["Financial Year", "Cluster", "hospital"],
            columns="Specialty",
            values="Hospital Beds",
            aggfunc="sum",
        )
        .reset_index()
        .rename(columns={"Financial Year": "fy", "Cluster": "bed_cluster"})
    )
    wide = wide.rename(columns=BED_SPECIALTY_MAP)
    for col in BED_SPECIALTY_MAP.values():
        if col not in wide.columns:
            wide[col] = 0.0
    wide = wide[["fy", "bed_cluster", "hospital"] + list(BED_SPECIALTY_MAP.values())]

    # 部分医院在 2017-18 前后改过名，映射后会出现同院两行 -> 相加合并
    wide = wide.groupby(["fy", "hospital"], as_index=False).sum(numeric_only=True)
    wide["bed_cluster"] = wide["hospital"].map(
        df.drop_duplicates("hospital").set_index("hospital")["Cluster"]
    )
    return wide.sort_values(["hospital", "fy"]).reset_index(drop=True)


def load_ae_annual(raw: pathlib.Path) -> pd.DataFrame:
    """HA 急症室年服务量：财政年度 × 医院。"""
    records = json.loads(require(raw / "ha/ae_attendances_annual.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df = df[~df["Hospital"].str.startswith("Overall")]   # 去掉联网汇总行
    df = df.rename(
        columns={
            "Financial Year": "fy",
            "Cluster": "ae_cluster",
            "Hospital": "hospital",
            "AE Attendances": "ae_annual",
        }
    )
    df["hospital"] = df["hospital"].replace(HOSPITAL_NAME_MAP)
    return (
        df[["fy", "hospital", "ae_annual"]]
        .groupby(["fy", "hospital"], as_index=False)["ae_annual"].sum()
        .sort_values(["hospital", "fy"])
        .reset_index(drop=True)
    )


def load_directory(raw: pathlib.Path) -> pd.DataFrame:
    """HA 设施名录：联网、是否有急症室、地址、经纬度。"""
    records = json.loads(require(raw / "ha/facility_hospitals.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(records)
    df = df.rename(
        columns={
            "cluster_eng": "facility_cluster",
            "institution_eng": "hospital",
            "with_AE_service_eng": "with_AE",
            "address_eng": "address",
            "latitude": "lat",
            "longitude": "lon",
        }
    )
    df["hospital"] = df["hospital"].replace(HOSPITAL_NAME_MAP)
    df["facility_cluster"] = df["facility_cluster"].replace(CLUSTER_NAME_MAP)
    cols = ["hospital", "facility_cluster", "with_AE", "address", "lat", "lon"]
    return df[cols].drop_duplicates("hospital").sort_values("hospital").reset_index(drop=True)


def load_hko(raw: pathlib.Path) -> pd.DataFrame:
    """香港天文台逐日气温，合并成 (date, temp_mean, temp_max, temp_min)。"""
    frames = []
    for code, name in HKO_DATA_TYPES.items():
        parts = []
        for year in HKO_YEARS:
            path = raw / f"hko/{code}_{year}.csv"
            if not path.exists():
                raise SystemExit(f"缺少原始文件：{path}\n请先执行：python pipeline/01_download.py")
            rows = []
            for line in path.read_text(encoding="utf-8-sig").splitlines()[2:]:  # 前两行为标题
                fields = [c.strip().strip('"') for c in line.split(",")]
                if len(fields) >= 4 and fields[0].isdigit():
                    value = fields[3]
                    rows.append(
                        {
                            "year": int(fields[0]),
                            "month": int(fields[1]),
                            "day": int(fields[2]),
                            name: float(value) if value not in ("", "N.A.", "***", "Trace") else None,
                        }
                    )
            parts.append(pd.DataFrame(rows))
        table = pd.concat(parts, ignore_index=True)
        table["date"] = pd.to_datetime(
            dict(year=table.year, month=table.month, day=table.day), errors="coerce"
        )
        frames.append(table.dropna(subset=["date"]).set_index("date")[[name]])

    hko = pd.concat(frames, axis=1).sort_index()
    return hko[~hko.index.duplicated(keep="first")]


# --------------------------------------------------------------------------
# S3  逐日 -> 逐周（对齐到流感周界）
# --------------------------------------------------------------------------
def aggregate_to_weeks(daily: pd.DataFrame, flu: pd.DataFrame) -> pd.DataFrame:
    """把 HA 逐日数据按流感周界聚合成 (联网, 医院, 周) 的均值。"""
    rows = []
    for r in flu.itertuples(index=False):
        window = daily[(daily["date"] >= r.week_start) & (daily["date"] <= r.week_end)]
        if window.empty:
            continue
        grouped = (
            window.groupby(["cluster", "hospital"])
            .agg(days=("date", "nunique"), **{c: (c, "mean") for c in OUTCOME_COLS})
            .reset_index()
        )
        grouped["week_start"] = r.week_start
        grouped["week_end"] = r.week_end
        grouped["season"] = r.season
        for col in FLU_COLS.values():
            grouped[col] = getattr(r, col)
        rows.append(grouped)
    return pd.concat(rows, ignore_index=True)


def aggregate_hko_to_weeks(hko: pd.DataFrame, flu: pd.DataFrame) -> pd.DataFrame:
    """气温按同一周界聚合成周均值。"""
    rows = []
    for r in flu.itertuples(index=False):
        window = hko.loc[(hko.index >= r.week_start) & (hko.index <= r.week_end)]
        rec = {"week_end": r.week_end, "temp_days": len(window)}
        for name in HKO_DATA_TYPES.values():
            rec[name] = window[name].mean() if len(window) else float("nan")
        rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# S4-S6  组装主表
# --------------------------------------------------------------------------
def build(raw: pathlib.Path, out: pathlib.Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)

    print("S1  读取原始文件")
    flu = load_flu(raw)
    surge = load_surge(raw)
    beds = load_beds(raw)
    ae_annual = load_ae_annual(raw)
    directory = load_directory(raw)
    hko = load_hko(raw)
    print(f"    流感速递        {len(flu):>6,} 周   {flu.week_end.min().date()} → {flu.week_end.max().date()}")
    print(f"    HA 高峰统计     {len(surge):>6,} 行   {surge.date.min().date()} → {surge.date.max().date()}")
    print(f"    HA 病床         {len(beds):>6,} 行   财政年度 {beds.fy.min()} → {beds.fy.max()}")
    print(f"    HA 年服务量     {len(ae_annual):>6,} 行")
    print(f"    HA 设施名录     {len(directory):>6,} 个机构")
    print(f"    天文台气温      {len(hko):>6,} 天   {hko.index.min().date()} → {hko.index.max().date()}")

    print("\nS2  统一医院/联网名称")
    surge_hospitals = sorted(set(surge.loc[surge.hospital != "HA Overall", "hospital"]))
    matched = sorted(set(surge_hospitals) & set(beds["hospital"]))
    unmatched = sorted(set(surge_hospitals) - set(beds["hospital"]))
    print(f"    高峰统计医院数         {len(surge_hospitals)}")
    print(f"    可对上病床年表         {len(matched)}/{len(surge_hospitals)}"
          + (f"   未对上：{unmatched}" if unmatched else ""))
    print(f"    名称对照规则           {HOSPITAL_NAME_MAP}")

    print("\nS3  HA 逐日 -> 逐周")
    weekly = aggregate_to_weeks(surge, flu)
    hospital_week = weekly[weekly.hospital != "HA Overall"].copy()
    hk_week = weekly[weekly.hospital == "HA Overall"].drop(columns=["cluster", "hospital"])
    print(f"    医院×周                {hospital_week.shape}")
    print(f"    全港周序列             {hk_week.shape}")

    print("\nS4  医院年度容量协变量")
    hospital_week["fy"] = hospital_week["week_end"].map(fiscal_year)
    panel = hospital_week.merge(beds.drop(columns=["bed_cluster"]), on=["fy", "hospital"], how="left")
    panel = panel.merge(ae_annual, on=["fy", "hospital"], how="left")
    panel = panel.merge(
        directory[["hospital", "with_AE", "lat", "lon"]], on="hospital", how="left"
    )
    print(f"    合并后                 {panel.shape}")

    print("\nS5  气温 -> 逐周")
    hko_week = aggregate_hko_to_weeks(hko, flu)
    print(f"    周气温                 {hko_week.shape}")

    print("\nS6  组装主表")
    panel = panel.merge(hko_week, on="week_end", how="left")
    hk_week = hk_week.merge(hko_week, on="week_end", how="left")

    # 列次序：标识 -> 结果 -> 暴露 -> 协变量 -> 时间覆盖
    order = (
        ["hospital", "cluster", "fy", "season", "week_start", "week_end"]
        + OUTCOME_COLS
        + list(FLU_COLS.values())
        + ["beds_acute", "beds_infirmary", "beds_mental", "beds_mh", "ae_annual", "with_AE", "lat", "lon"]
        + ["temp_mean", "temp_max", "temp_min", "temp_days", "days"]
        + ["week_in_season", "prev_gap_days"]
    )

    # 病床 / 年服务量只发布到 FY2024-25；之后沿用最后一年（病床为慢变量）
    for col in ["beds_acute", "beds_infirmary", "beds_mental", "beds_mh", "ae_annual"]:
        panel[col] = panel.groupby("hospital")[col].ffill()

    # 季节内周序 + 与上一周的间隔天数。
    # HA 并非每个冬季都连续发布（2023-24 起出现停发），因此直接 shift(1) 造滞后变量
    # 可能跨越数周空档。prev_gap_days > 7 即表示上一行并非真正的「上一周」，
    # 建模时必须据此屏蔽跨断档的滞后项。
    week_order = (
        panel[["season", "week_end"]]
        .drop_duplicates()
        .sort_values(["season", "week_end"])
        .reset_index(drop=True)
    )
    week_order["week_in_season"] = week_order.groupby("season").cumcount() + 1
    week_order["prev_gap_days"] = (
        week_order.groupby("season")["week_end"]
        .transform(lambda s: pd.to_datetime(s).diff().dt.days)
    )
    week_order["prev_gap_days"] = week_order["prev_gap_days"].fillna(0).astype(int)

    panel["week_end"] = pd.to_datetime(panel["week_end"])
    panel = panel.merge(
        week_order[["season", "week_end", "week_in_season", "prev_gap_days"]],
        on=["season", "week_end"],
        how="left",
    )
    hk_week["week_end"] = pd.to_datetime(hk_week["week_end"])
    hk_week = hk_week.merge(
        week_order[["season", "week_end", "week_in_season", "prev_gap_days"]],
        on=["season", "week_end"],
        how="left",
    )

    panel = panel[order].sort_values(["week_end", "hospital"]).reset_index(drop=True)
    print(f"    最终主表               {panel.shape}")
    n_gap = int((panel["prev_gap_days"] > 7).sum())
    print(f"    跨季节断档的周          {n_gap} 行（prev_gap_days > 7，最长达 "
          f"{int(panel['prev_gap_days'].max())} 天）")

    # -- 写出 ---------------------------------------------------------------
    panel.to_csv(out / "panel_hospital_week.csv", index=False)
    hk_week.to_csv(out / "hk_weekly.csv", index=False)
    beds.to_csv(out / "hospital_beds_annual.csv", index=False)
    ae_annual.to_csv(out / "ae_attendances_annual.csv", index=False)
    directory.to_csv(out / "hospital_directory.csv", index=False)
    write_data_dictionary(panel, hk_week, out / "data_dictionary.csv")

    print("\n产出：")
    for name in [
        "panel_hospital_week.csv",
        "hk_weekly.csv",
        "hospital_beds_annual.csv",
        "ae_attendances_annual.csv",
        "hospital_directory.csv",
        "data_dictionary.csv",
    ]:
        path = out / name
        print(f"    {name:32s} {path.stat().st_size:>10,} bytes")

    return {"panel": panel, "hk_week": hk_week}


# --------------------------------------------------------------------------
# 变量字典
# --------------------------------------------------------------------------
DATA_DICTIONARY = [
    ("hospital", "标识", "医院名称（已跨来源统一）", "分类型", "17 个值"),
    ("cluster", "标识", "医院所属医院联网", "分类型", "7 个值"),
    ("fy", "标识", "财政年度（4 月 1 日起算）", "分类型", "2019-20 … 2026-27"),
    ("season", "标识", "流感季标签（7 月为界）", "分类型", "8 个季节"),
    ("week_start", "标识", "该周第一天（周日）", "日期", "2019-11-25 …"),
    ("week_end", "标识", "该周最后一天（周六），对齐流感速递 To", "日期", "2019-12-07 … 2026-08-08"),
    ("ae_first_attend", "结果变量", "急症室首次求诊人次（周内日均）", "计数", "人次/日"),
    ("ae_to_med_ip", "结果变量", "经急症室转入内科住院人次（周内日均）", "计数", "人次/日"),
    ("med_bed_occ_rate", "结果变量", "内科病床占用率（周内日均）", "有界比例", "%"),
    ("ped_bed_occ_rate", "结果变量", "儿科病床占用率（周内日均）", "有界比例", "%"),
    ("ILI_PMP", "解释变量", "定点普通科门诊流感样病例比率【主解释变量】", "连续", "每千宗诊症"),
    ("ILI_AED", "解释变量", "急症室流感样病例比率", "连续", "每千宗诊症"),
    ("Adm_65", "解释变量", "65 岁及以上流感入院率", "连续", "每千人口"),
    ("Adm_All", "解释变量", "整体流感入院率", "连续", "每千人口"),
    ("Severe65", "解释变量", "65 岁及以上严重流感个案数", "计数", "宗/周"),
    ("flu_H1", "解释变量", "实验室确诊甲型 H1 流感病毒数", "计数", "宗/周"),
    ("flu_H3", "解释变量", "实验室确诊甲型 H3 流感病毒数", "计数", "宗/周"),
    ("flu_B", "解释变量", "实验室确诊乙型流感病毒数", "计数", "宗/周"),
    ("flu_AandB", "解释变量", "实验室确诊甲型+乙型流感病毒数", "计数", "宗/周"),
    ("beds_acute", "协变量", "急性及康复病床数（财政年度）", "连续", "张"),
    ("beds_infirmary", "协变量", "疗养病床数（财政年度）", "连续", "张"),
    ("beds_mental", "协变量", "精神科病床数（财政年度）", "连续", "张"),
    ("beds_mh", "协变量", "弱智科病床数（财政年度）", "连续", "张"),
    ("ae_annual", "协变量", "该院该财政年度急症室求诊总人次", "连续", "人次/年"),
    ("with_AE", "协变量", "该机构是否设急症室服务", "分类型", "Yes"),
    ("lat", "协变量", "医院纬度", "连续", "十进制度"),
    ("lon", "协变量", "医院经度", "连续", "十进制度"),
    ("temp_mean", "协变量", "香港天文台日平均气温（周内均值）", "连续", "°C"),
    ("temp_max", "协变量", "香港天文台日最高气温（周内均值）", "连续", "°C"),
    ("temp_min", "协变量", "香港天文台日最低气温（周内均值）", "连续", "°C"),
    ("temp_days", "数据质量", "该周有气温记录的天数", "计数", "0–7"),
    ("days", "数据质量", "该周 HA 实际发布数据的天数", "计数", "1–7"),
    ("week_in_season", "数据质量", "该周在其所属流感季内的序号", "计数", "1..N"),
    ("prev_gap_days", "数据质量",
     "与同季上一个已发布周的间隔天数。=7 表示真正相邻；>7 表示 HA 停发造成断档，"
     "构造滞后变量时必须据此屏蔽跨断档项", "计数", "0（该季首周）/ 7 / >7"),
]


def write_data_dictionary(panel: pd.DataFrame, hk_week: pd.DataFrame, path: pathlib.Path) -> None:
    rows = []
    for name, role, desc, dtype, unit in DATA_DICTIONARY:
        if name in panel.columns:
            col = panel[name]
            rows.append(
                {
                    "column": name,
                    "table": "panel_hospital_week",
                    "role": role,
                    "description": desc,
                    "dtype": dtype,
                    "unit": unit,
                    "n_non_null": int(col.notna().sum()),
                    "n_missing": int(col.isna().sum()),
                    "pct_missing": round(float(col.isna().mean() * 100), 2),
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", default=str(ROOT / "data" / "raw"), help="原始数据目录")
    ap.add_argument("--out-dir", default=str(ROOT / "data" / "processed"), help="产出目录")
    args = ap.parse_args()

    print("=" * 78)
    print("02_build.py — 构建分析面板")
    print("=" * 78)
    build(pathlib.Path(args.raw_dir), pathlib.Path(args.out_dir))
    print("\n✓ 完成。请接着执行 python pipeline/03_validate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
