import requests, pandas as pd, json
UA={"user-agent":"Mozilla/5.0"}
print("### FEHD historical archive (valid end date)")
r=requests.get("https://api.data.gov.hk/v1/historical-archive/list-file-versions",
  params={"url":"https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML",
          "start":"20200101","end":"20261009"},headers=UA,timeout=180)
print(r.status_code); 
try:
    j=r.json(); vs=j.get("versions",[])
    print("n_versions:", len(vs)); print(json.dumps(vs[:5],indent=1)); print("last:", vs[-3:] if vs else None)
except Exception as e: print(r.text[:500])

print("\n### censtatd 115-* table titles")
ids=["115-01011","115-01012","115-01012a","115-01013","115-01014","115-01015","115-01015a","115-01016",
     "115-01021","115-01022","115-01022a","115-01023","115-01031","115-01032","115-92001",
     "130-06102","930-92081","930-92082","930-92083","930-92084","930-92085","930-92086","930-92087","930-92088","930-92089","930-92090","930-92092","930-92093"]
for i in ids:
    try:
        d=requests.get("https://www.censtatd.gov.hk/api/get.php",params={"id":i,"lang":"en"},headers=UA,timeout=40).json()
        h=d.get("header",{})
        t=h.get("title"); n=h.get("count",{}).get("noOfRecords")
        dims=set()
        for row in d.get("dataSet",[])[:4000]: dims.update(k for k in row if k in ("SEX","AGE","CAUSE","freq","CD","ICD"))
        print(f"  {i:12s} n={str(n):6s} freq={sorted({r.get('freq') for r in d.get('dataSet',[])})} dims={sorted(dims)} :: {t}")
    except Exception as e:
        print(f"  {i:12s} ERR {e}")
