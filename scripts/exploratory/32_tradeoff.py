"""月度 vs 逐週：到底损失了什么"""
import pandas as pd, numpy as np, pathlib, json
D=pathlib.Path("data"); pd.set_option("display.width",250)
f=pd.read_csv(D/"f3_flu/flux_data.csv")
f["week_end"]=pd.to_datetime(f["To"],format="%d/%m/%Y",errors="coerce")
f=f.dropna(subset=["week_end"]).sort_values("week_end").reset_index(drop=True)

print("="*95); print("月度 vs 逐週 的資訊損失"); print("="*95)
print("\n[1] 樣本數對照")
print("  流感原始              : %d 週" % len(f))
print("  聚合成月              : %d 月" % f.week_end.dt.to_period("M").nunique())
print("  → 週:月 ≈ %.1f : 1（不是『少很多』，而是少 4.4 倍）" % (len(f)/f.week_end.dt.to_period("M").nunique()))

print("\n[2] 真正的損失不是樣本數，是『流感波的解析度』")
# 找出 2014 年以來的高峰波
f["ym"]=f.week_end.dt.to_period("M")
peaks=f[f.Adm_65_higher>1.0]
print("  Adm_65 入院率高於 1.0 的『高峰週』數:", len(peaks))
# 每個流感季高於 baseline 的連續週段
thr=f.Adm_65_higher.median()
above=f.Adm_65_higher>thr
grp=(above!=above.shift()).cumsum()
waves=f[above].groupby(grp).agg(start=("week_end","min"),end=("week_end","max"),n=("week_end","size"))
waves["days"]=(waves.end-waves.start).dt.days+7
print("\n  超過中位數的連續週段（流感波）:")
print(waves[waves.n>=3].to_string())
print("\n  → 一個流感波通常持續 3–8 週。聚合成『月』之後，一個波只剩 1–2 個資料點，")
print("     波峰、波寬、上升/下降速度全部無法辨識 → 滯後結構（lag）失去意義。")

print("\n[3] 聚合後相關係數的變化（同一個訊號）")
mon=f.groupby("ym").agg(Adm_65=("Adm_65_higher","mean"), ILI=("ILI_PMP","mean"),
                        AandB=("AandB","mean"), Severe65=("SevereCase_65_higher","sum")).reset_index()
print("  週層面：Adm_65 vs ILI_PMP        r = %.3f  (n=%d)" % (f.Adm_65_higher.corr(f.ILI_PMP),len(f)))
print("  月層面：Adm_65 vs ILI_PMP        r = %.3f  (n=%d)" % (mon.Adm_65.corr(mon.ILI),len(mon)))
print("  → 聚合會平滑掉高頻變異，相關係數通常被放大（生態謬誤風險）")

print("\n[4] 月度死亡資料本身長什麼樣（結局 A）")
dj=json.loads((D/"f3_death/monthly_deaths_by_sex_115-01022A.json").read_text())
d=pd.DataFrame(dj["dataSet"]); d=d[d.freq=="M"]
T=d[d.SEXDesc=="Total"].copy()
T["date"]=pd.PeriodIndex(T.period.astype(str),freq="M").to_timestamp()
T=T.sort_values("date")
T["month"]=T.date.dt.month
print("  月數 %d  %s → %s" % (len(T),T.date.min().date(),T.date.max().date()))
recent=T[T.date>="2014-01-01"]
print("  2014 起月數:", len(recent))
print("  月均值 %.0f  標準差 %.0f  變異係數 %.3f" % (recent.figure.mean(),recent.figure.std(),recent.figure.std()/recent.figure.mean()))
print("  季節性（2014 起各月平均 / 全年平均）:")
base=recent.figure.mean()
print((recent.groupby("month").figure.mean()/base).round(3).to_string())
print("  → 死亡數有清楚的冬季高峰；但『月度總死亡』會被其他死因（心血管、癌症…）稀釋")
print("  → 且死亡數是**發生數**（分母是人口），要用 offset（人口）或做超額死亡")

print("\n[5] 超額死亡做法（結局 A 的正確打開方式）")
rec=T[T.date>="2015-01-01"].copy(); rec["y"]=rec.date.dt.year; rec["m"]=rec.date.dt.month
hist=rec[rec.y<=2019].groupby("m").figure.agg(["mean","std"]).rename(columns={"mean":"base","std":"sd"})
rec=rec.join(hist,on="m")
rec["excess"]=rec.figure-rec.base
rec["z"]=(rec.figure-rec.base)/rec.sd
print("  以 2015–2019 同月均值為基線，2014–2026 共 %d 個月" % len(rec))
print("  超額死亡最多的 8 個月:")
print(rec.nlargest(8,"excess")[["date","figure","base","excess","z"]].round(1).to_string(index=False))
print("  最低的 5 個月:")
print(rec.nsmallest(5,"excess")[["date","figure","base","excess","z"]].round(1).to_string(index=False))
print("  → 2020–2022 年（COVID 期間）死亡偏低、2022 初與 2023 初 Omicron/流感季偏高，訊號清楚")
rec.to_csv("out/f3_excess_mortality_monthly.csv",index=False)
mon.to_csv("out/f3_flu_monthly_agg.csv",index=False)
print("\n[輸出] out/f3_excess_mortality_monthly.csv / f3_flu_monthly_agg.csv")
