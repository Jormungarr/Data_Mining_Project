import requests, json
UA={"user-agent":"Mozilla/5.0"}
r=requests.get("https://data.gov.hk/en-data/api/3/action/package_list",headers=UA,timeout=60).json()["result"]
cnt=[i for i in r if i.startswith("hk-censtatd-tablechart-")]
print("censtatd tablechart packages:", len(cnt))
import concurrent.futures as cf
def t(i):
    try:
        j=requests.get(f"https://data.gov.hk/en-data/api/3/action/package_show?id={i}",headers=UA,timeout=30).json()
        return i, j["result"]["title"], j["result"]["resources"][0]["url"]
    except Exception: return i,None,None
with cf.ThreadPoolExecutor(16) as ex:
    out=list(ex.map(t, cnt))
import re
pats={"RESTAURANT/CATERING":r"restaurant|catering|food service",
      "DEATH/MORTALITY":r"death|mortal",
      "FLU/INFLUENZA":r"influenza|flu ",
      "HOTEL/VISITOR":r"hotel|visitor|tourism"}
for k,p in pats.items():
    print("\n#####",k)
    for i,ti,u in out:
        if ti and re.search(p,ti,re.I): print(f"  {i:38s} {ti[:100]}")
