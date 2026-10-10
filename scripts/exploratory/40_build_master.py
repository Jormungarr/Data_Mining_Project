"""構建方案三完整分析數據集：逐日 → 逐週 → 醫院×週面板 + 年度協變量"""
import pandas as pd, numpy as np, pathlib, json, re
D=pathlib.Path("data"); out=pathlib.Path("out"); pd.set_option("display.width",250)

NAME_FIX={"Ruttonjee & Tang Shiu Kin Hospitals":"Ruttonjee Hospital"}   # surge 名 -> 其他來源名
CLUSTER_FIX={"Hong Kong Island Cluster":"Hong Kong East/West"}
def fy(d):  # 日期 -> 財政年度 (4月制)
    d=pd.Timestamp(d); y=d.year if d.month>=4 else d.year-1
    return f"{y}-{str(y+1)[2:]}"

# ---------- 來源 ----------
fac=pd.DataFrame(json.loads((D/"ha_extra/facility_hosp.json").read_text()))[
      ["cluster_eng","institution_eng","with_AE_service_eng","address_eng","latitude","longitude"]]
fac.columns=["cluster_raw","hospital","with_AE","address","lat","lon"]
fac["cluster"]=fac.cluster_raw.replace(CLUSTER_FIX)
fac["hospital"]=fac.hospital.replace(NAME_FIX)

bed=pd.DataFrame(json.loads((D/"ha_extra/hosp_bed.json").read_text()))
bed=bed[bed.Specialty!="Overall"]
bed=bed.pivot_table(index=["Financial Year","Cluster","Hospital"],columns="Specialty",
                    values="Hospital Beds",aggfunc="sum").reset_index()
bed.columns=[str(c) for c in bed.columns]
bed=bed.rename(columns={"Financial Year":"fy","Cluster":"bed_cluster","Hospital":"hospital",
    "General (Acute and Convalescent)":"beds_acute","Infirmary":"beds_infirmary",
    "Mentally Ill":"beds_mental","Mentally Handicapped":"beds_mh"})
bed["hospital"]=bed.hospital.replace(NAME_FIX)
bed=bed.groupby(["fy","hospital"],as_index=False).sum(numeric_only=True)   # 合併舊/新院名的兩段序列

ae=pd.DataFrame(json.loads((D/"ha_extra/ae_attnd.json").read_text()))
ae=ae[~ae.Hospital.str.startswith("Overall")].rename(columns={
    "Financial Year":"fy","Cluster":"ae_cluster","Hospital":"hospital","AE Attendances":"ae_annual"})
ae["hospital"]=ae.hospital.replace(NAME_FIX)

# ---------- 流感（週） ----------
flu=pd.read_csv(D/"f3_flu/flux_data.csv")
flu["week_end"]=pd.to_datetime(flu["To"],format="%d/%m/%Y",errors="coerce")
flu=flu.dropna(subset=["week_end"]).sort_values("week_end").reset_index(drop=True)

# ---------- HA surge（日） ----------
surge=pd.DataFrame(json.loads((D/"f3_ha/daily_services_en.json").read_text()))
surge["date"]=pd.to_datetime(surge.date)
NUM=["ae_first_attend","ae_to_med_ip","med_bed_occ_rate","ped_bed_occ_rate"]

def to_week(df,daily=True):
    rows=[]
    for _,r in flu.iterrows():
        w0=r.week_end-pd.Timedelta(days=6)
        sl=df[(df.date>=w0)&(df.date<=r.week_end)]
        if len(sl)==0: continue
        g=sl.groupby(["cluster","hospital"]).agg(days=("date","nunique"),
              **{c:(c,"mean") for c in NUM}).reset_index()
        g["week_start"]=w0; g["week_end"]=r.week_end
        g["season"]=f"{r.week_end.year-1}-{str(r.week_end.year)[2:]}" if r.week_end.month<7 else f"{r.week_end.year}-{str(r.week_end.year+1)[2:]}"
        for k,src in [("ILI_PMP","ILI_PMP"),("ILI_AED","ILI_AED"),("Adm_65","Adm_65_higher"),
                      ("Adm_All","Adm_All"),("Severe65","SevereCase_65_higher"),
                      ("flu_H1","H1"),("flu_H3","H3"),("flu_B","B"),("flu_AandB","AandB")]:
            g[k]=r[src]
        rows.append(g)
    return pd.concat(rows,ignore_index=True)

W=to_week(surge)                                    # 含 HA Overall（hospital==""）
W["hospital"]=W.hospital.replace("","HA Overall")
W["fy"]=W.week_end.map(fy)

# ---------- 掛協變量 ----------
Pan=W[W.hospital!="HA Overall"].copy()
Pan["hospital"]=Pan.hospital.replace(NAME_FIX)      # surge 名 -> 統一院名
Pan=Pan.merge(bed,on=["fy","hospital"],how="left")
Pan=Pan.merge(ae[["fy","hospital","ae_annual"]],on=["fy","hospital"],how="left")
Pan=Pan.merge(fac[["hospital","with_AE","lat","lon"]].drop_duplicates("hospital"),on="hospital",how="left")
# 專科不存在 = 0 床（pivot 後 NaN）；先限定在已配對的列
for c in ["beds_acute","beds_infirmary","beds_mental","beds_mh"]:
    Pan.loc[Pan.fy.isin(bed.fy.unique()),c]=Pan.loc[Pan.fy.isin(bed.fy.unique()),c].fillna(0)
# 病床/服務量只到 FY2024-25 → 之後沿用最後一年（容量是慢變量）
for c in ["beds_acute","beds_infirmary","beds_mental","beds_mh","ae_annual"]:
    Pan[c]=Pan.groupby("hospital")[c].ffill()
HA=W[W.hospital=="HA Overall"].drop(columns=["hospital"])

print("="*100); print("最終分析數據集"); print("="*100)
print("\n[A] 醫院×週面板:", Pan.shape)
print("      醫院", Pan.hospital.nunique(), "間  週", Pan.week_end.nunique(), " 季節", Pan.season.nunique(),"個")
print("      完全7天覆蓋:", (Pan.days==7).sum(), "列")
print("\n    協變量覆蓋率:")
for c in ["beds_acute","beds_infirmary","beds_mental","beds_mh","ae_annual","lat","lon"]:
    print(f"      {c:16s} {Pan[c].notna().mean()*100:5.1f}%")
print("\n    缺失率（關鍵變量）:")
for c in NUM+["ILI_PMP","Adm_65","flu_AandB","Severe65"]:
    print(f"      {c:20s} {Pan[c].isna().mean()*100:5.1f}%")

print("\n[B] HA Overall 週序列:", HA.shape, " 週", HA.week_end.nunique())

print("\n[C] 各醫院年度容量協變量（FY2023-24 為例）")
t=Pan[Pan.fy=="2023-24"].drop_duplicates("hospital")[
   ["cluster","hospital","beds_acute","beds_infirmary","beds_mental","ae_annual"]]
print(t.sort_values("beds_acute",ascending=False).to_string(index=False))

print("\n[D] 各院流感彈性初探（週層面相關）")
cc=Pan.dropna(subset=["ae_first_attend","ILI_PMP"]).groupby("hospital").apply(
        lambda g: g.ae_first_attend.corr(g.ILI_PMP),include_groups=False).sort_values(ascending=False)
print(cc.round(3).to_string())

Pan.to_csv(out/"f3_panel_hospital_week.csv",index=False)
HA.to_csv(out/"f3_hk_weekly.csv",index=False)
bed.to_csv(out/"f3_bed_capacity_annual.csv",index=False)
ae.to_csv(out/"f3_ae_attendance_annual.csv",index=False)
print("\n[輸出]")
for f in ["f3_panel_hospital_week.csv","f3_hk_weekly.csv","f3_bed_capacity_annual.csv","f3_ae_attendance_annual.csv"]:
    p=out/f; print(f"   out/{f}  {p.stat().st_size:,} bytes")
