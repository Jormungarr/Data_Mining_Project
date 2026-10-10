import pandas as pd, numpy as np, pathlib
out=pathlib.Path("out"); pd.set_option("display.width",250)
P=pd.read_csv(out/"f3_panel_hospital_week.csv",parse_dates=["week_start","week_end"])
H=pd.read_csv(out/"f3_hk_weekly.csv",parse_dates=["week_start","week_end"])
print("="*100); print("最終數據集驗證"); print("="*100)
print("\n[1] 醫院×週面板（主表）", P.shape)
print("  欄位:"); 
for c in P.columns: print(f"     {c:22s} {str(P[c].dtype):10s} 缺失{P[c].isna().mean()*100:5.1f}%")
print("\n  面板平衡性: 17 院 × 144 週 =", 17*144, " 實際", len(P))
print("  每院週數:", P.groupby("hospital").size().unique())
print("  每季週數:", P.groupby("season").week_end.nunique().to_dict())
print("\n[2] 數值摘要")
print(P[["ae_first_attend","ae_to_med_ip","med_bed_occ_rate","ped_bed_occ_rate",
         "ILI_PMP","Adm_65","flu_AandB","Severe65","beds_acute","ae_annual"]].describe().T.round(2).to_string())
print("\n[3] 季節描述（HA Overall 層面）", H.shape)
print(H.groupby("season").agg(週數=("week_end","nunique"),
      AE均值=("ae_first_attend","mean"), AE峰值=("ae_first_attend","max"),
      佔用率均值=("med_bed_occ_rate","mean"), 佔用率峰值=("med_bed_occ_rate","max"),
      ILI均值=("ILI_PMP","mean")).round(1).to_string())
print("\n[4] 異質性：各院 流感↔急症室 相關（週層面）")
r=P.dropna(subset=["ae_first_attend","ILI_PMP"]).groupby("hospital").apply(
   lambda g: pd.Series({"r_ae":g.ae_first_attend.corr(g.ILI_PMP),
                        "r_bed":g.med_bed_occ_rate.corr(g.ILI_PMP),
                        "beds":g.beds_acute.iloc[0], "ae_yr":g.ae_annual.iloc[0]}),
   include_groups=False).sort_values("r_ae",ascending=False)
print(r.round(3).to_string())
print("\n  r_ae 範圍: %.3f ~ %.3f" % (r.r_ae.min(), r.r_ae.max()))
print("\n[5] 覆蓋時間軸")
print("  流感+HA 共同覆蓋: %s → %s (%d 週)" % (P.week_start.min().date(),P.week_end.max().date(),P.week_end.nunique()))
print("  但只有 %d 個冬季窗口，非連續（見 season 分佈）" % P.season.nunique())
