import requests, pathlib, re, json, concurrent.futures as cf
UA={"user-agent":"Mozilla/5.0"}; D=pathlib.Path("data")
def pkg(i): return requests.get(f"https://data.gov.hk/en-data/api/3/action/package_show?id={i}",headers=UA,timeout=60).json()["result"]
def get(u,p):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and p.stat().st_size>0: return ("skip",p)
    try:
        r=requests.get(u,headers=UA,timeout=120); r.raise_for_status(); p.write_bytes(r.content); return ("ok",p)
    except Exception as e: return (f"ERR {type(e).__name__}",p)

jobs=[]
# --- F1 journey time: all CSV resources for all years
p=pkg("hk-td-tis_34-car-journey-time-data")
for r in p["resources"]:
    if r["format"]=="CSV":
        nm=re.sub(r"[^\w\.\-]","_",r["url"].rsplit("/",1)[-1])
        jobs.append((r["url"], D/"f1_traffic"/nm))
# --- F1 AQHI: every month
p=pkg("hk-epd-airteam-past-record-of-air-quality-health-index-en")
for r in p["resources"]:
    m=re.search(r"/(\d{6})_Eng\.csv",r["url"])
    if m: jobs.append((r["url"], D/"f1_aqhi"/f"{m.group(1)}_Eng.csv"))
# --- F2
for u,pth in [
 ("https://www.ha.org.hk/opendata/pas_report/Daily_Services_Statistics/Daily_Services_Statistics_EN.json", D/"f3_ha/daily_services_en.json"),
 ("https://www.ha.org.hk/opendata/pas_report/Daily_Services_Statistics/Daily_Services_Statistics_EN.xlsx", D/"f3_ha/daily_services_en.xlsx"),
]:
    jobs.append((u,pth))
for i,sub in [("hk-censtatd-tablechart-625-68003","f2_rest"),("hk-censtatd-tablechart-650-80001","f2_visitor")]:
    rid=i.split("tablechart-")[1].upper()
    jobs.append((f"https://www.censtatd.gov.hk/api/get.php?id={rid}&lang=en&full_series=1", D/sub/f"{rid}.json"))

with cf.ThreadPoolExecutor(12) as ex:
    res=list(ex.map(lambda j: get(*j), jobs))
ok=sum(1 for s,_ in res if s in("ok","skip")); bad=[(s,str(p)) for s,p in res if s.startswith("ERR")]
print(f"downloaded/kept: {ok}/{len(jobs)}")
for b in bad[:20]: print("  ",b)
print("f1_aqhi files:", len(list((D/'f1_aqhi').glob('*.csv'))))
print("f1_traffic files:", len(list((D/'f1_traffic').glob('*.csv'))))
