import requests, json, pandas as pd, pathlib
UA={"user-agent":"Mozilla/5.0"}; D=pathlib.Path("data")
def api(i,**kw):
    p={"id":i,"lang":"en","full_series":1}; p.update(kw)
    return requests.get("https://www.censtatd.gov.hk/api/get.php",params=p,headers=UA,timeout=90).json()

print("### 115-01022A monthly deaths-by-sex: freq/period range")
d=api("115-01022A"); ds=d["dataSet"]
df=pd.DataFrame(ds); print(df.groupby("freq").agg(n=("period","size"), lo=("period","min"), hi=("period","max")))
m=df[df.freq=="M"]; print("monthly rows:",len(m)); print(m.tail(4).to_string())
print("dims:", sorted({k for r in ds for k in r}))

print("\n### 625-68003 Restaurant receipts by type of restaurant")
d2=api("625-68003"); ds2=d2["dataSet"]; df2=pd.DataFrame(ds2)
print("title:",d2["header"]["title"])
print(df2.groupby("freq").agg(n=("period","size"), lo=("period","min"), hi=("period","max")))
print("keys:", [k for k in df2.columns if k not in ("figure","sd_value")])
print(df2.head(3).to_string())

print("\n### 650-80001 visitor arrivals coverage")
d3=api("650-80001"); df3=pd.DataFrame(d3["dataSet"])
print("title:",d3["header"]["title"])
print(df3.groupby("freq").agg(n=("period","size"), lo=("period","min"), hi=("period","max")))

print("\n### HA key statistics during surge")
r=requests.get("https://data.gov.hk/en-data/api/3/action/package_show?id=hospital-hadata-key-statistics-during-surge",headers=UA,timeout=60).json()["result"]
print(r["title"],"|",(r.get("notes") or "")[:250])
for x in r["resources"][:6]: print("   R:",x["name"],"|",x["format"],"|",x["url"])
