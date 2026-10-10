#!/usr/bin/env python3
"""
03_model.py - baseline model: influenza activity -> A&E first attendances.

This is a starting template. It fits the simple specification recommended in
DATA_GUIDE Section 7.2: one predictor, one response, hospital and season fixed
effects. Extend it once this works end to end.

Reads:
    data/processed/panel_hospital_week.csv

Writes:
    out/model_baseline.txt      fitted model summary
    out/model_coefficients.csv  tidy coefficient table
    out/model_fitted.png        observed vs fitted, territory-wide

Usage:
    python pipeline/03_model.py
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")          # write files without needing a display
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import dmatrices

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Same expectations the validator enforces, so a bad input fails loudly here too.
EXPECTED_ROWS = 2448
EXPECTED_COLS = 34


def load_panel(path: pathlib.Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Cannot find {path}\nRun this first: python pipeline/01_build.py")

    df = pd.read_csv(path)
    if df.shape != (EXPECTED_ROWS, EXPECTED_COLS):
        raise SystemExit(
            f"Unexpected panel shape {df.shape}; expected ({EXPECTED_ROWS}, {EXPECTED_COLS}).\n"
            f"Rebuild with: python pipeline/01_build.py"
        )
    return df


def add_lag(df: pd.DataFrame, col: str, lag: int = 1) -> pd.DataFrame:
    """One-week lag of `col`, computed within season and masked across HA gaps.

    The panel is eight separate winter windows, so shifting the whole table would
    pull a value from several weeks back across a publication gap and label it
    'last week'. See DATA_GUIDE Section 4.2.
    """
    df = df.sort_values(["season", "week_end"]).copy()
    out = df.groupby("season")[col].shift(lag)
    # prev_gap_days > 7 means this week does not actually follow the previous row
    out[df["prev_gap_days"] > 7] = np.nan
    df[f"{col}_lag{lag}"] = out
    return df


def fit_model(df: pd.DataFrame, formula: str, cluster_by: str = "week_end"):
    """Fit a negative binomial regression and estimate the dispersion parameter.

    Two details matter here, and both are easy to get wrong.

    1. `smf.glm(..., family=sm.families.NegativeBinomial())` is NOT used: that
       class takes alpha, the dispersion, as a fixed input and silently defaults
       to alpha=1.0. `sm.NegativeBinomial` estimates alpha from the data.

    2. Standard errors are clustered by WEEK, not by hospital. The influenza
       predictor is a territory-wide series: all 17 hospitals share the same value
       each week, so the residual correlation is *across hospitals within a week*,
       not *within a hospital over time*. Clustering by hospital is the intuitive
       choice and it is wrong here — with only 17 clusters and a nearly common
       regressor, the cluster-robust variance is biased sharply downwards and
       p-values become spuriously tiny. Clustering by week uses the 144 units over
       which the predictor actually varies.
    """
    y, X = dmatrices(formula, data=df, return_type="dataframe")
    model = sm.NegativeBinomial(y.values.ravel(), X.values)
    result = model.fit(disp=0, maxiter=200, cov_type="cluster",
                       cov_kwds={"groups": df[cluster_by].values})
    return result, X.columns.tolist(), model


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel", default=str(ROOT / "data" / "processed" / "panel_hospital_week.csv"))
    ap.add_argument("--out-dir", default=str(ROOT / "out"))
    ap.add_argument("--formula", default=None, help="override the model formula")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("03_model.py - baseline model")
    print("=" * 78)

    print("\n1  Load panel")
    df = load_panel(pathlib.Path(args.panel))
    print(f"   {df.shape[0]:,} rows x {df.shape[1]} cols, "
          f"{df.hospital.nunique()} hospitals, {df.week_end.nunique()} weeks")

    print("\n2  Build features")
    df = add_lag(df, "ILI_PMP", lag=1)
    # C() turns a text column into dummy variables, i.e. fixed effects.
    formula = args.formula or "ae_first_attend ~ ILI_PMP + ILI_PMP_lag1 + C(hospital) + C(season)"
    print(f"   formula: {formula}")
    model_df = df.dropna(subset=["ae_first_attend", "ILI_PMP", "ILI_PMP_lag1"]).copy()
    print(f"   estimation sample: {len(model_df):,} rows "
          f"(lost {len(df) - len(model_df)} to the lag and to missing responses)")

    print("\n3  Fit negative binomial regression (dispersion estimated from the data)")
    result, term_names, model = fit_model(model_df, formula)
    alpha = result.params[-1]
    print(f"   converged: {result.mle_retvals['converged']},  AIC: {result.aic:,.1f}")
    print(f"   dispersion alpha = {alpha:.4f}  "
          f"({'overdispersed' if alpha > 0.01 else 'close to Poisson'})")
    print(f"   standard errors clustered by week ({model_df.week_end.nunique()} clusters)")

    print("\n4  Coefficients of interest")
    tidy = pd.DataFrame({
        "term": term_names + ["alpha"],
        "coef": result.params,
        "std_err": result.bse,
        "z": result.tvalues,
        "p_value": result.pvalues,
    })
    tidy["ci_low"] = tidy.coef - 1.96 * tidy.std_err
    tidy["ci_high"] = tidy.coef + 1.96 * tidy.std_err
    tidy["exp_coef"] = np.exp(tidy.coef)

    focus = tidy[tidy.term.isin(["ILI_PMP", "ILI_PMP_lag1"])]
    for r in focus.itertuples():
        print(f"   {r.term:14s} coef={r.coef:+.4f}  SE={r.std_err:.4f}  "
              f"p={r.p_value:.4g}  rate ratio={r.exp_coef:.4f}")
    print("   Interpretation: a one-unit rise in ILI_PMP multiplies expected daily")
    print("   A&E attendances by exp(coef), holding hospital and season fixed.")

    print("\n5  Why cluster by week? Comparing standard errors")
    idx = term_names.index("ILI_PMP")
    variants = [
        ("model-based (assumes independence)", {}),
        ("clustered by hospital (17)", dict(cov_type="cluster", cov_kwds={"groups": model_df["hospital"].values})),
        ("clustered by week (144)  <- used", dict(cov_type="cluster", cov_kwds={"groups": model_df["week_end"].values})),
    ]
    for label, kw in variants:
        r = model.fit(disp=0, maxiter=200, **kw)
        print(f"   {label:38s} SE={r.bse[idx]:.5f}   p={r.pvalues[idx]:.3g}")
    print("   Clustering by hospital shrinks the SE because there are only 17 clusters")
    print("   and the predictor barely varies within them. Clustering by week is correct.")

    print("\n6  Write outputs")
    (out_dir / "model_baseline.txt").write_text(result.summary().as_text(), encoding="utf-8")
    tidy.to_csv(out_dir / "model_coefficients.csv", index=False)
    print(f"   out/model_baseline.txt")
    print(f"   out/model_coefficients.csv  ({len(tidy)} terms)")

    # Territory-wide observed vs fitted. The x-axis uses real dates so the eight
    # winter windows appear with the publication gaps between them, rather than
    # being squeezed into an evenly spaced sequence that looks continuous.
    model_df["fitted"] = result.predict(exog=result.model.exog)
    weekly = model_df.groupby("week_end")[["ae_first_attend", "fitted"]].mean()
    weekly.index = pd.to_datetime(weekly.index)
    # Reindex onto a complete weekly grid so the missing weeks become NaN. This
    # breaks the line at each publication gap instead of drawing a straight
    # segment across it, which would imply data we do not have.
    grid = pd.date_range(weekly.index.min(), weekly.index.max(), freq="7D")
    weekly = weekly.reindex(grid)
    ax = weekly.plot(figsize=(11, 4.5), color=["#1f4e79", "#c0504d"],
                     linewidth=1.6, marker="o", markersize=2.5)
    ax.set_xlabel("week ending")
    ax.set_ylabel("A&E first attendances per day")
    ax.set_title("Observed vs fitted, averaged over hospitals")
    ax.legend(["observed", "fitted"])
    ax.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_dir / "model_fitted.png", dpi=150)
    plt.close()
    print(f"   out/model_fitted.png")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
