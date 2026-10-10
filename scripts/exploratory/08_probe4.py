import requests, json, collections, pathlib
from lxml import etree
UA={"user-agent":"Mozilla/5.0"}
print("### distinct tags in restaurant XML")
root=etree.parse("data/f2_licence/LP_Restaurants_EN.XML").getroot()
tags=collections.Counter(el.tag for el in root.iter())
print(dict(tags))
lps=root.findall(".//LP"); print("n_licences:", len(lps))
print("child tags of LP:", [c.tag for c in lps[0]])
dates=collections.Counter()
for lp in lps:
    for c in lp:
        if "DATE" in c.tag and c.text: dates[c.tag]+=1
print("date-ish fields:", dict(dates))
print("sample LP:", etree.tostring(lps[0],pretty_print=True).decode()[:400])

print("\n### CSDI dataset metadata for restaurant licences")
for ds in ["fehd_rcd_1630036390312_58893"]:
    for base in ["https://portal.csdi.gov.hk/server/services/catalog/query"]:
        pass
try:
    r=requests.get("https://api.csdi.gov.hk/geoportal/api/v1/datasets/fehd_rcd_1630036390312_58893",headers=UA,timeout=60)
    print(r.status_code, r.text[:400])
except Exception as e: print("ERR",e)

print("\n### censtatd tables (full_series=1)")
for i in ["115-01011","115-01013","115-01014","115-01015","115-01016","115-01021","115-01022","115-01022a","115-01023","115-01031","115-01032","115-92001"]:
    try:
        d=requests.get("https://www.censtatd.gov.hk/api/get.php",params={"id":i,"lang":"en","full_series":1},headers=UA,timeout=60).json()
        h=d.get("header",{}); ds=d.get("dataSet",[])
        dims=sorted({k for r in ds[:5000] for k in r if k in ("SEX","AGE","CAUSE","freq","CD","ICD","sv")})
        print(f"  {i:12s} n={len(ds):6d} dims={dims} :: {h.get('title')}")
    except Exception as e: print(f"  {i} ERR {e}")
