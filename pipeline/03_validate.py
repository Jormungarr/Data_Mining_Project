#!/usr/bin/env python3
"""
03_validate.py — 对 data/processed/ 的产出做完整性、一致性与合理性检查。

检查分四类：
    A. 结构        行数、主键唯一性、面板平衡性、列数
    B. 时间       周界定义、季节内连续性、季节归属
    C. 一致性      跨来源数值勾稽（各院之和 vs HA Overall）
    D. 分布        取值范围、缺失率、结构性常量

任一检查失败则退出码为 1，可用于 CI。

用法：
    python pipeline/03_validate.py
    python pipeline/03_validate.py --out-dir data/processed --report out/validation_report.txt
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent

OUTCOME_COLS = ["ae_first_attend", "ae_to_med_ip", "med_bed_occ_rate", "ped_bed_occ_rate"]
FLU_COLS = ["ILI_PMP", "ILI_AED", "Adm_65", "Adm_All", "Severe65", "flu_H1", "flu_H3", "flu_B", "flu_AandB"]
CAPACITY_COLS = ["beds_acute", "beds_infirmary", "beds_mental", "beds_mh", "ae_annual"]

EXPECTED_ROWS = 2448
EXPECTED_HOSPITALS = 17
EXPECTED_WEEKS = 144
EXPECTED_COLS = 34

# 取值范围合理区间（宽松边界，只用于捕捉明显错误，不做数据剪裁）
RANGE_CHECKS = {
    "ae_first_attend": (50, 800),
    "ae_to_med_ip": (0, 300),
    "med_bed_occ_rate": (40, 160),
    "ped_bed_occ_rate": (0, 160),
    "ILI_PMP": (0, 200),
    "Adm_65": (0, 20),
    "temp_mean": (0, 40),
    "temp_max": (0, 45),
    "temp_min": (-5, 35),
    "lat": (22.0, 22.6),
    "lon": (113.8, 114.5),
}

# 已知且已记录在案的缺失模式：医院 -> {列: 期望缺失率下限(%)}
EXPECTED_MISSING = {
    "North Lantau Hospital": {"ae_to_med_ip": 99.0, "med_bed_occ_rate": 99.0, "ped_bed_occ_rate": 99.0},
}


class Report:
    """收集检查结果，最后统一打印并写文件。"""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def section(self, title: str) -> None:
        self.lines.append("")
        self.lines.append("=" * 78)
        self.lines.append(title)
        self.lines.append("=" * 78)

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {label}"
        if detail:
            line += f"  —  {detail}"
        self.lines.append(line)
        if not ok:
            self.failures.append(f"{label}  {detail}")
        return ok

    def warn(self, label: str, detail: str = "") -> None:
        self.lines.append(f"  [WARN] {label}" + (f"  —  {detail}" if detail else ""))
        self.warnings.append(f"{label}  {detail}")

    def note(self, text: str) -> None:
        self.lines.append(f"         {text}")

    def render(self) -> str:
        self.lines.append("")
        self.lines.append("=" * 78)
        if self.failures:
            self.lines.append(f"结论：{len(self.failures)} 项检查未通过")
            for f in self.failures:
                self.lines.append(f"  ✗ {f}")
        else:
            self.lines.append("结论：全部检查通过")
        if self.warnings:
            self.lines.append(f"另有 {len(self.warnings)} 项警告：")
            for w in self.warnings:
                self.lines.append(f"  ! {w}")
        self.lines.append("=" * 78)
        return "\n".join(self.lines)


def check_structure(r: Report, panel: pd.DataFrame, hk: pd.DataFrame) -> None:
    r.section("A. 结构")
    r.check(len(panel) == EXPECTED_ROWS, "行数 = 2,448", f"实际 {len(panel):,}")
    r.check(
        panel.hospital.nunique() == EXPECTED_HOSPITALS,
        "医院数 = 17",
        f"实际 {panel.hospital.nunique()}",
    )
    r.check(
        panel.week_end.nunique() == EXPECTED_WEEKS,
        "周数 = 144",
        f"实际 {panel.week_end.nunique()}",
    )
    r.check(
        len(panel) == panel.hospital.nunique() * panel.week_end.nunique(),
        "面板完全平衡（无缺行）",
        f"{panel.hospital.nunique()} × {panel.week_end.nunique()} = {len(panel):,}",
    )
    dup = panel.duplicated(subset=["hospital", "week_end"]).sum()
    r.check(dup == 0, "主键 (hospital, week_end) 唯一", f"重复 {dup} 行")
    r.check(panel.columns.duplicated().sum() == 0, "无重复列名")
    if len(panel.columns) != EXPECTED_COLS:
        r.warn("列数不为预期", f"预期 {EXPECTED_COLS}，实际 {len(panel.columns)}")
    else:
        r.check(True, f"列数 = {EXPECTED_COLS}", f"实际 {len(panel.columns)}")
    r.check(len(hk) == EXPECTED_WEEKS, "全港周序列 = 144 行", f"实际 {len(hk)}")


def check_time(r: Report, panel: pd.DataFrame) -> None:
    r.section("B. 时间轴")
    # 周界：week_end - week_start 必须恰为 6 天
    span = (pd.to_datetime(panel.week_end) - pd.to_datetime(panel.week_start)).dt.days
    r.check(bool((span == 6).all()), "每周 week_start → week_end 恰为 7 天", f"跨度值 {sorted(span.unique())}")

    # 季节归属：以 7 月为界
    we = pd.to_datetime(panel.week_end)
    expected_season = np.where(
        we.dt.month < 7,
        (we.dt.year - 1).astype(str) + "-" + we.dt.year.astype(str).str[2:],
        we.dt.year.astype(str) + "-" + (we.dt.year + 1).astype(str).str[2:],
    )
    mismatch = int((expected_season != panel.season.values).sum())
    r.check(mismatch == 0, "季节标签与 7 月分界一致", f"不符 {mismatch} 行")

    # 季节内周连续性：HA 并非每个冬季都连续发布，故不要求连续，
    # 但要求「断档必须被 prev_gap_days 正确标记」，否则跨断档的滞后变量会出错。
    r.note("季节内连续性（HA 停发会造成断档，必须被 prev_gap_days 标记）：")
    gap_rows = 0
    for season, grp in panel.groupby("season"):
        weeks = pd.Series(sorted(pd.to_datetime(grp.week_end.unique())))
        diffs = weeks.diff().dt.days.dropna()
        gaps = diffs[diffs != 7]
        n_gap_weeks = int((grp["prev_gap_days"] > 7).sum() // panel.hospital.nunique())
        gap_rows += n_gap_weeks
        r.note(
            f"    {season}: {len(weeks):>2} 周  {weeks.iloc[0].date()} → {weeks.iloc[-1].date()}"
            + (f"   断档 {len(gaps)} 处（间隔 {sorted(set(gaps.astype(int)))} 天），涉及 {n_gap_weeks} 个周"
               if len(gaps) else "   连续")
        )
    r.check(gap_rows > 0, "断档已被识别", f"共 {gap_rows} 个周紧随断档之后（prev_gap_days > 7）")

    # prev_gap_days 的定义校验：>=7 时必等于真实间隔；=0 只允许出现在季节首周
    per_week = panel.drop_duplicates(["season", "week_end"])[["season", "week_end", "week_in_season", "prev_gap_days"]].copy()
    per_week["week_end"] = pd.to_datetime(per_week.week_end)
    per_week = per_week.sort_values(["season", "week_end"])
    true_gap = per_week.groupby("season")["week_end"].diff().dt.days.fillna(0).astype(int)
    r.check(bool((true_gap.values == per_week["prev_gap_days"].values).all()),
            "prev_gap_days 与真实周间隔完全一致",
            f"不符 {int((true_gap.values != per_week['prev_gap_days'].values).sum())} 处")

    # week_in_season 应从 1 连续编号
    ok_wi = True
    for season, grp in per_week.groupby("season"):
        if list(grp.week_in_season) != list(range(1, len(grp) + 1)):
            ok_wi = False
    r.check(ok_wi, "week_in_season 在每个季节内从 1 连续编号")

def check_consistency(r: Report, panel: pd.DataFrame, hk: pd.DataFrame, out_dir: pathlib.Path) -> None:
    r.section("C. 跨来源一致性")
    # 各院之和应≈ HA Overall（周均值的和 vs 全港日均；两者口径不同，只做量级校验）
    per_week_sum = panel.groupby("week_end")["ae_first_attend"].sum().rename("sum_hospitals")
    merged = hk.set_index("week_end")["ae_first_attend"].rename("ha_overall").to_frame().join(per_week_sum)
    merged["ratio"] = merged.sum_hospitals / merged.ha_overall
    lo, hi = merged.ratio.min(), merged.ratio.max()
    r.check(
        0.70 <= lo and hi <= 1.30,
        "各院急症室求诊之和 与 HA Overall 量级一致",
        f"比值范围 {lo:.3f} – {hi:.3f}（应≈1；差异来自各院独立取整与均值口径）",
    )

    # 病床/年服务量必须 100% 覆盖
    for col in CAPACITY_COLS:
        pct = panel[col].isna().mean() * 100
        r.check(pct == 0.0, f"容量协变量 {col} 无缺失", f"缺失率 {pct:.2f}%")

    # 医院名录坐标覆盖
    r.check(panel["lat"].isna().sum() == 0, "所有医院均有坐标", f"缺失 {int(panel['lat'].isna().sum())} 行")

    # 气温覆盖
    r.check(panel["temp_mean"].isna().sum() == 0, "所有周均有气温记录",
            f"缺失 {int(panel['temp_mean'].isna().sum())} 行")
    r.check(bool((panel["temp_days"] == 7).all()), "每周气温天数均为 7 天",
            f"取值 {sorted(panel['temp_days'].unique())}")

    # 独立复算：直接读原始 HA 文件核对总行数与日期数
    raw_surge = out_dir.parent / "raw" / "ha" / "service_demand_surge_daily.json"
    if raw_surge.exists():
        import json
        recs = json.loads(raw_surge.read_text(encoding="utf-8"))
        daily = pd.DataFrame(recs)
        r.check(len(daily) == 16704, "原始 HA 高峰统计行数 = 16,704", f"实际 {len(daily):,}")
        n_days_overall = daily[daily.cluster == "HA Overall"]["date"].nunique()
        r.check(n_days_overall == 928, "HA Overall 覆盖天数 = 928", f"实际 {n_days_overall}")
    else:
        r.warn("找不到原始 HA 文件，跳过独立复算", str(raw_surge))


def check_distribution(r: Report, panel: pd.DataFrame) -> None:
    r.section("D. 取值与缺失")

    r.note("取值范围检查（宽松边界，仅捕捉明显错误）：")
    for col, (lo, hi) in RANGE_CHECKS.items():
        if col not in panel.columns:
            continue
        s = pd.to_numeric(panel[col], errors="coerce").dropna()
        out_of_range = int(((s < lo) | (s > hi)).sum())
        ok = out_of_range == 0
        r.check(ok, f"{col} 落在 [{lo}, {hi}]", f"越界 {out_of_range} 个，实际范围 [{s.min():.2f}, {s.max():.2f}]")

    r.note("")
    r.note("缺失率（按变量）：")
    for col in OUTCOME_COLS + FLU_COLS + CAPACITY_COLS:
        pct = panel[col].isna().mean() * 100
        r.note(f"    {col:20s} {pct:6.2f}%")

    r.note("")
    r.note("结构性事实：流感暴露变量在同一周内对 17 家医院取相同值（无截面变异）")
    for col in FLU_COLS:
        nunique = panel.groupby("week_end")[col].nunique()
        ok = bool((nunique == 1).all())
        r.check(ok, f"{col} 每周仅 1 个取值", f"异常周数 {int((nunique != 1).sum())}")

    r.note("")
    r.note("已知缺失模式的确认：")
    for hospital, expectations in EXPECTED_MISSING.items():
        sub = panel[panel.hospital == hospital]
        if sub.empty:
            r.warn(f"预期缺失的医院不存在于面板中：{hospital}")
            continue
        for col, min_pct in expectations.items():
            actual = sub[col].isna().mean() * 100
            r.check(actual >= min_pct, f"{hospital} / {col} 仍为高缺失", f"实际 {actual:.1f}%（预期 ≥ {min_pct}%）")

    r.note("")
    r.note("儿科占用率覆盖（仅设有儿科服务的医院有值）：")
    ped = panel.groupby("hospital")["ped_bed_occ_rate"].apply(lambda s: s.notna().mean() * 100).round(1)
    n_ped = int((ped > 50).sum())
    n_none = int((ped < 5).sum())
    n_partial = 17 - n_ped - n_none
    r.note(f"    完整覆盖 {n_ped} 院；完全无覆盖 {n_none} 院；部分覆盖 {n_partial} 院")
    r.note("    完整：" + ", ".join(f"{h.split()[0]}({p:.0f}%)" for h, p in ped.items() if p > 50))
    r.note("    无：" + ", ".join(f"{h.split()[0]}" for h, p in ped.items() if p < 5))
    if n_partial:
        r.note("    部分：" + ", ".join(f"{h.split()[0]}({p:.0f}%)" for h, p in ped.items() if 5 <= p <= 50))
    r.check(n_ped + n_none + n_partial == 17, "儿科覆盖可完全归类（合计 17 院）",
            f"{n_ped} + {n_none} + {n_partial} = 17")
    r.check(n_ped >= 10, "儿科子样本足够建模（≥10 院）", f"实际 {n_ped} 院")

    r.note("")
    r.note("各变量基本统计：")
    desc = panel[OUTCOME_COLS + FLU_COLS + ["temp_mean", "beds_acute", "ae_annual"]].describe().T
    for name, row in desc.iterrows():
        r.note(f"    {name:20s} n={int(row['count']):>5d}  mean={row['mean']:>10.2f}  sd={row['std']:>9.2f}  "
               f"min={row['min']:>8.2f}  max={row['max']:>8.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "data" / "processed"))
    ap.add_argument("--report", default=str(ROOT / "out" / "validation_report.txt"))
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    panel_path = out_dir / "panel_hospital_week.csv"
    hk_path = out_dir / "hk_weekly.csv"
    if not panel_path.exists():
        raise SystemExit(f"找不到 {panel_path}\n请先执行：python pipeline/02_build.py")

    panel = pd.read_csv(panel_path)
    hk = pd.read_csv(hk_path)

    r = Report()
    r.lines.append("=" * 78)
    r.lines.append("03_validate.py — 分析面板验证报告")
    r.lines.append("=" * 78)
    r.lines.append(f"  主表   {panel_path}   {panel.shape[0]:,} 行 × {panel.shape[1]} 列")
    r.lines.append(f"  全港表 {hk_path}   {hk.shape[0]:,} 行 × {hk.shape[1]} 列")

    check_structure(r, panel, hk)
    check_time(r, panel)
    check_consistency(r, panel, hk, out_dir)
    check_distribution(r, panel)

    text = r.render()
    print(text)

    report_path = pathlib.Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    print(f"\n报告已写入 {report_path}")

    return 1 if r.failures else 0


if __name__ == "__main__":
    sys.exit(main())
