"""方案一可行性实测：車輛車程時間資料 × 過去AQHI記錄 × 2021人口普查"""
import pandas as pd, numpy as np, pathlib, re, csv, json
D=pathlib.Path("data"); out=pathlib.Path("out"); out.mkdir(exist_ok=True)
pd.set_option("display.width",220)

print("="*95); print("方案一 TEST — 車輛車程時間 × 空氣質素健康指數(AQHI) × 2021人口普查"); print("="*95)

# ---------- 1. 車程時間：真實欄位 ----------
def readcsv(f):
    b=pathlib.Path(f).read_bytes()
    for enc in ("utf-8-sig","utf-8","big5hkscs","cp1252","latin-1"):
        try: t=b.decode(enc); break
        except Exception: continue
    return list(csv.reader(t.splitlines()))

def parse_jt(f):
    rr=readcsv(f)
    for i,r in enumerate(rr):
        if r and r[0].strip() in ("Road/Street","Origin - Destination"):
            return i, r, (rr[i+1] if i+1<len(rr) else [])
    return None,None,None

recs=[]; schemas={}
for f in sorted((D/"f1_traffic").glob("*.csv")):
    yr=int(re.search(r"(20\d\d)",f.name).group(1))
    hi,hdr,hdr2=parse_jt(f); rr=readcsv(f)
    body=[r for r in rr[hi+2:] if r and r[0].strip()]
    key=("TABLE4(STREET)" if hdr[0]=="Road/Street" else "TABLE2(O-D ROUTE)")
    schemas.setdefault(key,set()).add(tuple(x.strip() for x in hdr if x.strip()))
    recs.append(dict(file=f.name,year=yr,layout=key,n_units=len(body)))
info=pd.DataFrame(recs)

print("\n[1a] 車程時間 CSV 的欄位結構（48 個檔）")
for k,v in schemas.items():
    print(f"  {k}:")
    for s in sorted(v): print("     欄位 =", " | ".join(s))
print("\n  → 欄位只有 距離(km) 與 行程時間(分鐘)；**沒有任何月份 / 季度 / 日期欄位**")

print("\n[1b] 可用的時間鍵")
print(info.groupby(["layout","year"]).agg(files=("file","size"),units=("n_units","sum")).to_string())
print("\n  年度清單：", sorted(info.year.unique()), " → 只有 3 個時間點（年度平均）")

# ---------- 2. AQHI ----------
files=sorted((D/"f1_aqhi").glob("*.csv"))
def load_aqhi(f):
    rr=readcsv(f)
    hi=next((i for i,r in enumerate(rr) if r and r[0].strip()=="Date"), None)
    if hi is None: return None
    hdr=[c.strip() for c in rr[hi]]
    body=[r for r in rr[hi+1:] if len(r)>=2]
    n=len(hdr)
    body=[(r+[""]*n)[:n] for r in body]
    d=pd.DataFrame(body, columns=hdr)
    d["Date"]=d["Date"].replace("",np.nan).ffill()
    d=d[d["Hour"].astype(str).str.strip()!="Daily Max"].copy()
    d["month"]=f.stem[:6]; return d
aq=pd.concat([x for x in map(load_aqhi,files) if x is not None],ignore_index=True)
stations=[c for c in aq.columns if c not in ("Date","Hour","month")]
print("\n[2] AQHI 粒度")
print(f"  檔案 {len(files)} 個月 / 觀測 {len(aq):,} 筆 / 監測站 {len(stations)}")
print("  月份範圍:", aq.month.min(),"→",aq.month.max(), " 時間鍵 = (日期, 小時, 監測站)")
for s in stations: aq[s]=pd.to_numeric(aq[s].astype(str).str.replace("*",""),errors="coerce")
mon=aq.groupby("month")[stations].mean()

# ---------- 3. 交集 ----------
print("\n[3] 三者能不能拼？")
jt_years=sorted(info.year.unique()); aq_years=sorted({int(m[:4]) for m in mon.index})
print("  車程時間時間鍵 :", jt_years, " (年度)")
print("  AQHI 時間鍵    :", f"{aq_years[0]}–{aq_years[-1]}", " (月度/小時)")
inter=sorted(set(jt_years)&set(aq_years))
print(f"  → 年度交集 = {inter}，共 {len(inter)} 期")
print(f"  → 若以 (路段×方向) 為觀測單位，n = 3；以年度均值做回歸，樣本數 3 << 參數數")

# ---------- 4. 地理鍵 ----------
print("\n[4] 地理鍵對齊")
grp=sorted({re.sub(r"_(20\d\d)\.csv$","",f.name) for f in (D/"f1_traffic").glob("*.csv")})
print("  車程時間檔名分組（表內無分區欄位）：")
for g in grp: print("     -",g)
cen=pd.read_csv(D/"f1_census/DC_21C.CSV")
print(f"  AQHI 空間鍵   = {len(stations)} 個監測站")
print(f"  人口普查空間鍵 = {cen.iloc[:,1].nunique()} 個區議會分區")
print("  → 車程時間以『路段』為單位；三份資料無共同主鍵，需人工建立 路段↔監測站↔分區 對照表")

info.to_csv(out/"f1_journey_files.csv",index=False)
mon.to_csv(out/"f1_aqhi_monthly_station_mean.csv")
mon.mean(axis=1).to_csv(out/"f1_aqhi_monthly_hk_mean.csv",header=["aqhi_hk_mean"])
print("\n[輸出] out/f1_journey_files.csv / f1_aqhi_monthly_station_mean.csv / f1_aqhi_monthly_hk_mean.csv")

print("\n[結論] 方案一：**核心拼接不成立**")
print("   - 車程時間只有 2023/2024/2025 三個年度橫截面，無月度/季度 → 無法與逐小時 AQHI 做時間序列對齊")
print("   - 若要保留方案一，必須改設計：把主資料換成有月度粒度的交通指標")
print("     （例如 hk-td-tis_17 Monthly Traffic and Transport Digest，或 hk-td-sm_8 即時車程指標累積）")
