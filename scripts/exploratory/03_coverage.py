import re, json, requests, pandas as pd, pathlib
UA={"user-agent":"Mozilla/5.0"}; D=pathlib.Path("data")
def pkg(i):
    return requests.get(f"https://data.gov.hk/en-data/api/3/action/package_show?id={i}",headers=UA,timeout=60).json()["result"]

# --- journey time: which years exist?
p=pkg("hk-td-tis_34-car-journey-time-data")
yrs=sorted({int(m.group(1)) for r in p["resources"] for m in [re.search(r"(20\d\d)\.(csv|xlsx)$",r["url"])] if m})
print("JOURNEY-TIME years available:", yrs, "| n_resources:", len(p["resources"]))
print("  any monthly?  ->", [r["name"] for r in p["resources"] if re.search(r"month|jan|feb|quarter", r["name"], re.I)][:5] or "NO")

# --- AQHI total months
p2=pkg("hk-epd-airteam-past-record-of-air-quality-health-index-en")
ms=sorted({m.group(1) for r in p2["resources"] for m in [re.search(r"(\d{6})_Eng\.csv",r["url"])] if m})
print("\nAQHI months:", len(ms), ms[0], "->", ms[-1])

# --- hotel occupancy
h=pd.read_csv(D/"f2_hotel/hotel_room_occupancy_rate_monthly_by_district_en.csv")
print("\nHOTEL cols:", list(h.columns))
print(h.head(3).to_string()); print(h.tail(3).to_string())
print("rows:",len(h), "range:", h.iloc[0,0], "->", h.iloc[-1,0], "dtypes:", set(map(str,h.dtypes)))

# --- census zip
import zipfile
z=pathlib.Path(D/"f1_census/DC_21C.zip")
with zipfile.ZipFile(z) as zf: zf.extractall("data/f1_census/")
c=pd.read_csv("data/f1_census/DC_21C.CSV")
print("\nCENSUS shape:",c.shape)
print(c.head(4).to_string()[:1200])
print("cols:",list(c.columns)[:40])
