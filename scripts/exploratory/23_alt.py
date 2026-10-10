import requests,re
UA={"user-agent":"Mozilla/5.0"}
p=requests.get("https://data.gov.hk/en-data/api/3/action/package_show?id=hk-td-tis_17-monthly-traffic-and-transport-digest-csv",headers=UA,timeout=60).json()["result"]
print("MTTD resources:",len(p["resources"]))
hits=[r for r in p["resources"] if re.search(r"journey|speed|time|travel",r["name"],re.I)]
print("含 journey/speed/travel 的資源:")
for r in hits: print("   ",r["name"][:110],"|",r["url"])
print("\n所有 Section 標題:")
secs=sorted({re.match(r"(Section \d+[^:]*|Chart \d+[^:]*|Table \d+[^:-]*)",r["name"]).group(1).strip() for r in p["resources"] if re.match(r"(Section|Chart|Table)",r["name"])})
for s in secs: print("   ",s)
