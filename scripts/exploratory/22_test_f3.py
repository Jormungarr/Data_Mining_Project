"""方案三可行性實測：流感速遞（週） × 死亡統計（月/年） × HA 每日服務量"""
import pandas as pd, numpy as np, pathlib, json
import statsmodels.api as sm, statsmodels.formula.api as smf
D=pathlib.Path("data"); out=pathlib.Path("out"); out.mkdir(exist_ok=True)
pd.set_option("display.width",240)

print("="*95); print("方案三 TEST — 流感監測（週） × 死亡統計 × 醫療系統壓力"); print("="*95)

# ---------- 1. 流感週資料 ----------
f=pd.read_csv(D/"f3_flu/flux_data.csv")
f["week_end"]=pd.to_datetime(f["To"],format="%d/%m/%Y",errors="coerce")
print("\n[1] 流感速遞圖表數據 (hk-dh-chpsebcddr-flu-express)")
print(f"  週數 {len(f)} / 範圍 {f.week_end.min().date()} → {f.week_end.max().date()} / 欄位 {len(f.columns)}")
key=["ILI_PMP","ILI_FMC","AandB","H1","H3","B","Adm_All","Adm_65_higher","Adm_0_5",
     "SevereCase_65_higher","SevereCase_50_64","ILI_AED","Fever_RCHE"]
print("  關鍵欄位缺失率:")
for c in key: print(f"     {c:22s} {f[c].isna().mean()*100:5.1f}%")
print("  → 週粒度、時間序列長（2014 起約 666 週），可直接做時間序列")

# ---------- 2. 死亡統計 ----------
dj=json.loads((D/"f3_death/monthly_deaths_by_sex_115-01022A.json").read_text())
dd=pd.DataFrame(dj["dataSet"])
print("\n[2] 死亡統計")
m=dd[(dd.freq=="M")]
print("  Table 115-01022A 月度死亡（按性別）: 期數",m.period.nunique()," 範圍",m.period.min(),"→",m.period.max())
print("  維度:", sorted({k for k in dd.columns if k not in ('figure','sd_value')}), " → 只有 SEX，**沒有 AGE、沒有 CAUSE**")
aj=json.loads((D/"f3_death/deaths_by_sex_age_115-01022.json").read_text())
ad=pd.DataFrame(aj["dataSet"])
print("  Table 115-01022 死亡（按性別+年齡組）: freq =", sorted(ad.freq.unique()), " → **只有年度**")
ages=sorted(ad.AGEDesc.dropna().unique()); print("  年齡組:", ages)
dh=pd.read_csv(D/"f3_death/deaths_by_leading_cause_en.csv",header=5)
print("  DH NCDD 主要死因: shape",dh.shape," 首欄:",dh.columns[0])
print("   → 亦為**年度**（2001–2024），且無年齡拆分")

# ---------- 3. 對齊 ----------
print("\n[3] 時間對齊")
T=dd[(dd.freq=="M")&(dd.SEXDesc=="Total")].copy()
T["ym"]=T.period.astype(str); T["date"]=pd.to_datetime(T.ym,format="%Y%m")
T=T[["date","figure"]].rename(columns={"figure":"deaths_total"}).sort_values("date")
print("  月度死亡: %d 個月 %s → %s" % (len(T),T.date.min().date(),T.date.max().date()))
f["ym"]=f.week_end.dt.to_period("M").astype(str)
mon=f.groupby("ym").agg(weeks=("week_end","size"), ILI_PMP=("ILI_PMP","mean"),
                        Adm_65_high=("Adm_65_higher","mean"), Adm_All=("Adm_All","mean"),
                        AandB=("AandB","mean"), Severe65=("SevereCase_65_higher","sum")).reset_index()
mon["date"]=pd.PeriodIndex(mon.ym,freq="M").to_timestamp()
print("  流感(週→月): %d 個月 %s → %s" % (len(mon),mon.date.min().date(),mon.date.max().date()))
J=T.merge(mon,on="date",how="inner").dropna(subset=["deaths_total","ILI_PMP","Adm_65_high"])
print("  內連接後: %d 個月（%s → %s）" % (len(J),J.date.min().date(),J.date.max().date()))
print("  → 週資料可以降頻到月對齊；但**對齊後就丟掉週解析度**")
print("  → 想要『週』對齊，死亡端必須有週資料；data.gov.hk 上沒有 → 這是方案三的硬限制")

# ---------- 4. 實測：能不能建模 ----------
print("\n[4] 建模實測（月度水平）")
J=J.sort_values("date").reset_index(drop=True)
for lag in [0,1,2]:
    J[f"ili_l{lag}"]=J.ILI_PMP.shift(lag)
    J[f"adm65_l{lag}"]=J.Adm_65_high.shift(lag)
J["month"]=J.date.dt.month
sub=J.dropna()
print("  建模樣本 n =",len(sub))
X=sm.add_constant(sub[["ili_l0","ili_l1","ili_l2","adm65_l0","adm65_l1"]])
ols=sm.OLS(sub.deaths_total,X).fit()
print("  OLS  (deaths ~ ILI lags + Adm65 lags):  R2=%.3f  AIC=%.1f" % (ols.rsquared, ols.aic))
print(ols.params.round(2).to_string())
nb=smf.glm("deaths_total ~ ili_l0 + ili_l1 + adm65_l0 + adm65_l1",data=sub,
           family=sm.families.NegativeBinomial()).fit()
print("  NB-GLM:  deviance=%.0f  AIC=%.1f" % (nb.deviance, nb.aic))
print("  相關係數 (月死亡數 vs 同月 ILI): %.3f" % sub.deaths_total.corr(sub.ili_l0))
print("  → 計數回歸在月度層面**跑得通**（負二項優於泊松的正規做法）")

# ---------- 5. HA 每日 ----------
print("\n[5] 補充：醫管局每日服務量（可有週/日解析度）")
ha=pd.DataFrame(json.loads((D/"f3_ha/daily_services_en.json").read_text()))
ha["date"]=pd.to_datetime(ha.date)
ov=ha[ha.cluster=="HA Overall"]
print("  全部欄位:", list(ha.columns), " 筆數:", len(ha))
print("  HA Overall 日數:",ov.date.nunique()," 範圍",ov.date.min().date(),"→",ov.date.max().date())
print("  HA Overall 指標:", [c for c in ha.columns if c not in ("surge_year","date","cluster","hospital")])
haf=ha[ha.cluster!="HA Overall"].groupby("date")[["ae_first_attend","ae_to_med_ip"]].sum().reset_index()
JJ=J.merge(haf,on="date",how="inner")
print("  與流感月資料可對齊月數:", len(JJ))
w=f.copy(); w["date"]=w.week_end
HW=haf.merge(w[["date"]],on="date")
print("  週層面：HA 每日 → 可聚合成週；與流感週資料共同覆蓋週數 =", len(HW))

J.to_csv(out/"f3_flu_deaths_monthly.csv",index=False)
mon.to_csv(out/"f3_flu_monthly.csv",index=False)
haf.to_csv(out/"f3_ha_daily_totals.csv",index=False)
print("\n[輸出] out/f3_flu_deaths_monthly.csv / f3_flu_monthly.csv / f3_ha_daily_totals.csv")

print("\n[結論] 方案三：**部分成立**")
print("   ✔ 流感速遞：週粒度、2014 起、含 ILI 就診率 / 入院率 / 嚴重個案，品質好")
print("   ✘ 死亡統計沒有『週 × 65+ × 呼吸系統疾病』這個切片：")
print("        - 月度只有『按性別』（無年齡、無死因）")
print("        - 年齡拆分只有年度；死因拆分（DH NCDD）也只有年度")
print("   ✔ 可行改法：把結局換成『月度總死亡數』或『月度超額死亡』，或改用 HA 每日服務量當結局")
print("   ✔ 課程契合點仍然成立：時間序列 + 計數回歸（NB）+ 變化點檢測 + 模型評估")
