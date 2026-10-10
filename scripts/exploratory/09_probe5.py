import requests, json
UA={"user-agent":"Mozilla/5.0"}
def pkg(i):
    r=requests.get(f"https://data.gov.hk/en-data/api/3/action/package_show?id={i}",headers=UA,timeout=60).json()
    return r.get("result") if r.get("success") else {"name":i,"error":r.get("error")}

for i in ["hk-td-tis_10-monthly-traffic-and-transport-digest","hk-td-tis_17-monthly-traffic-and-transport-digest-csv"]:
    p=pkg(i); print("=====",p.get("name")); print("  T:",p.get("title")); print("  N:",(p.get("notes") or "")[:300])
    for r in p.get("resources",[])[:10]: print("   R:",r["name"],"|",r["format"],"|",r["url"])

print("\n### censtatd 130-06* (catering) and 930-92* (health) tables")
for i in ["130-06102","130-06103","130-06601","130-06601a","130-06602","130-06605",
          "930-92081","930-92082","930-92083","930-92084","930-92085","930-92086","930-92087","930-92088","930-92089","930-92090","930-92092","930-92093"]:
    try:
        d=requests.get("https://www.censtatd.gov.hk/api/get.php",params={"id":i,"lang":"en","full_series":1},headers=UA,timeout=60).json()
        h=d.get("header",{}); ds=d.get("dataSet",[])
        dims=sorted({k for r in ds[:6000] for k in r if k in ("SEX","AGE","CAUSE","freq","CD","ICD","sv","TYPE")})
        pers=sorted({str(r.get("period")) for r in ds})[:2]
        print(f"  {i:12s} n={len(ds):6d} freq={sorted({r.get('freq') for r in ds})} dims={dims} per={pers} :: {h.get('title')}")
    except Exception as e: print(f"  {i} ERR {e}")
