"""HA 資料的可建模面板：逐日 / 逐週 / 逐醫院"""
import pandas as pd, numpy as np, pathlib, json
D=pathlib.Path("data"); out=pathlib.Path("out")
pd.set_option("display.width",250)
ha=pd.DataFrame(json.loads((D/"f3_ha/daily_services_en.json").read_text()))
ha["date"]=pd.to_datetime(ha.date)

print("="*95); print("[4] 數值分佈與缺失"); print("="*95)
num=["ae_first_attend","ae_to_med_ip","med_bed_occ_rate","ped_bed_occ_rate"]
print(ha[num].describe().T.to_string())
print("\n  缺失率:")
for c in num: print(f"     {c:20s} {ha[c].isna().mean()*100:5.1f}%")

print("\n[5] 逐醫院明細（各院出現天數 / 缺失）")
h=ha[ha.cluster!="HA Overall"].groupby(["cluster","hospital"]).agg(
    days=("date","nunique"), ae_na=("ae_first_attend",lambda s:s.isna().mean()),
    bed_na=("med_bed_occ_rate",lambda s:s.isna().mean())).reset_index()
print(h.to_string())

print("\n[6] HA Overall 每季描述統計")
ov=ha[ha.cluster=="HA Overall"].copy()
print(ov.groupby("surge_year")[num].agg(["mean","max"]).round(1).to_string())

# ---- 逐週面板 ----
print("\n"+"="*95); print("[7] 與流感資料合成的逐週面板"); print("="*95)
f=pd.read_csv(D/"f3_flu/flux_data.csv")
f["week_end"]=pd.to_datetime(f["To"],format="%d/%m/%Y",errors="coerce")
f=f.dropna(subset=["week_end"])
# HA 每日 -> 每週（以流感週的結束日為週界：往前 6 天）
d_ov=ov.set_index("date")[num]
rows=[]
for _,r in f.iterrows():
    w0=r.week_end-pd.Timedelta(days=6)
    sl=d_ov.loc[(d_ov.index>=w0)&(d_ov.index<=r.week_end)]
    rec=dict(week_end=r.week_end, n_days=len(sl))
    for c in num: rec[c]=sl[c].mean()
    rec.update(ILI_PMP=r.ILI_PMP, Adm_65=r.Adm_65_higher, Adm_All=r.Adm_All,
               AandB=r.AandB, Severe65=r.SevereCase_65_higher)
    rows.append(rec)
W=pd.DataFrame(rows)
W["season"]=W.week_end.apply(lambda d: f"{d.year-1}-{str(d.year)[2:]}" if d.month<7 else f"{d.year}-{str(d.year+1)[2:]}")
full=W.dropna(subset=["ae_first_attend","ILI_PMP"])
print("  流感週總數:", len(f))
print("  HA 有覆蓋的週數（n_days>0）:", (W.n_days>0).sum())
print("  HA 完整 7 天的週數        :", (W.n_days==7).sum())
print("  可建模週數（HA+流感都有） :", len(full))
print("  季節分佈:"); print(full.season.value_counts().sort_index().to_string())
print("\n  可用週的數值預覽:")
print(full[["week_end","season","n_days","ae_first_attend","med_bed_occ_rate","ILI_PMP","Adm_65","Severe65"]].tail(12).to_string(index=False))

print("\n[8] 相關性（週層面, n=%d）"%len(full))
cc=full[["ae_first_attend","ae_to_med_ip","med_bed_occ_rate","ILI_PMP","Adm_65","Adm_All","AandB"]].corr().round(3)
print(cc.to_string())

# 逐醫院長面板
print("\n"+"="*95); print("[9] 逐醫院 × 逐週的長面板（真正的大樣本）"); print("="*95)
hosp=ha[ha.cluster!="HA Overall"].copy()
rows=[]
for _,r in f.iterrows():
    w0=r.week_end-pd.Timedelta(days=6)
    sl=hosp[(hosp.date>=w0)&(hosp.date<=r.week_end)]
    if len(sl)==0: continue
    a=sl.groupby(["cluster","hospital"]).agg(days=("date","nunique"),
        ae=("ae_first_attend","mean"), ip=("ae_to_med_ip","mean"),
        bed=("med_bed_occ_rate","mean")).reset_index()
    a["week_end"]=r.week_end; a["ILI_PMP"]=r.ILI_PMP; a["Adm_65"]=r.Adm_65_higher
    a["Severe65"]=r.SevereCase_65_higher; a["AandB"]=r.AandB
    rows.append(a)
L=pd.concat(rows,ignore_index=True)
L["season"]=L.week_end.apply(lambda d: f"{d.year-1}-{str(d.year)[2:]}" if d.month<7 else f"{d.year}-{str(d.year+1)[2:]}")
print("  長面板規模:", L.shape, " = 18 間醫院 × %d 週"%L.week_end.nunique())
print("  完全覆蓋 7 天的列數:", (L.days==7).sum())
print("  每間醫院的週數:"); print(L.groupby("hospital").week_end.nunique().to_string())
print("\n  可用自由度: 18 醫院 × 約 %d 週 = %d 個觀測" % (L.week_end.nunique(), 18*L.week_end.nunique()))
print(L.dropna(subset=["ae"]).head(6)[["week_end","season","cluster","hospital","ae","bed","ILI_PMP"]].to_string(index=False))

W.to_csv(out/"f3_ha_weekly_hk.csv",index=False)
L.to_csv(out/"f3_ha_hospital_week_panel.csv",index=False)
full.to_csv(out/"f3_ha_flu_weekly_merged.csv",index=False)
print("\n[輸出] out/f3_ha_weekly_hk.csv / f3_ha_hospital_week_panel.csv / f3_ha_flu_weekly_merged.csv")
