"""抓取 HKO 開放數據：逐日平均/最高/最低氣溫 (2019-2026)"""
import requests, pathlib, pandas as pd, time
UA={"user-agent":"Mozilla/5.0"}
D=pathlib.Path("data/hko"); D.mkdir(parents=True,exist_ok=True)
B="https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
VAR={"CLMTEMP":"temp_mean","CLMMAXT":"temp_max","CLMMINT":"temp_min"}
frames=[]
for code,name in VAR.items():
    parts=[]
    for yr in range(2019,2027):
        for attempt in range(3):
            try:
                r=requests.get(B,params={"dataType":code,"lang":"en","rformat":"csv",
                                         "year":yr,"station":"HKO"},headers=UA,timeout=60)
                if "Please include" in r.text: raise RuntimeError("invalid params")
                pathlib.Path(D/f"{code}_{yr}.csv").write_bytes(r.content)
                t=r.text
                parts.append(t); break
            except Exception as e:
                if attempt==2: print(f"  ERR {code} {yr}: {e}")
                time.sleep(1)
    # 解析：前 2 行是標題，第 3 行是欄名
    rows=[]
    for t in parts:
        ls=[x for x in t.splitlines() if x.strip()]
        for ln in ls[2:]:
            f=[c.strip().strip('"') for c in ln.split(",")]
            if len(f)>=4 and f[0].isdigit():
                rows.append(dict(year=int(f[0]),month=int(f[1]),day=int(f[2]),
                                 value=float(f[3]) if f[3] not in ("","N.A.","***") else None))
    d=pd.DataFrame(rows)
    d["date"]=pd.to_datetime(dict(year=d.year,month=d.month,day=d.day),errors="coerce")
    d=d.dropna(subset=["date"]).rename(columns={"value":name})[["date",name]]
    print(f"  {code} -> {name}: {len(d)} 天  {d.date.min().date()} → {d.date.max().date()}  缺失 {d[name].isna().sum()}")
    frames.append(d.set_index("date"))
hko=pd.concat(frames,axis=1).sort_index()
hko.to_csv(D/"hko_daily_temperature.csv")
print("\n合併後:", hko.shape, " → data/hko/hko_daily_temperature.csv")
print(hko.describe().round(2).to_string())
print("\n每年天數:"); print(hko.groupby(hko.index.year).size().to_string())
