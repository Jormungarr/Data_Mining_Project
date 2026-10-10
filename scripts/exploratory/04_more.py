import requests, pandas as pd, json, pathlib, re
UA={"user-agent":"Mozilla/5.0"}; D=pathlib.Path("data")

print("########## FEHD historical archive API probe")
u="https://api.data.gov.hk/v1/historical-archive/list-file-versions"
r=requests.get(u,params={"url":"https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML","start":"20200101","end":"20261010"},headers=UA,timeout=120)
print(r.status_code, r.text[:600])

print("\n########## Flu data coverage")
f=pd.read_csv(D/"f3_flu/flux_data.csv")
print("shape",f.shape)
f["date"]=pd.to_datetime(f["From"],format="%d/%m/%Y",errors="coerce")
print("week range:", f["date"].min(), "->", f["date"].max())
print("cols:", list(f.columns))
print("Adm_65_higher nonnull:", f["Adm_65_higher"].notna().sum(), "/", len(f))
print("ILI_PMP nonnull:", f["ILI_PMP"].notna().sum())
print("\n2014 nonnull per col:"); print(f[f.Year==2014].notna().sum().to_string())
print("\n2024 nonnull per col:"); print(f[f.Year==2024].notna().sum().to_string())

print("\n########## search censtatd death-by-age/cause tables on data.gov.hk")
for q in ["deaths age group","monthly deaths","death cause","mortality"]:
    j=requests.get("https://data.gov.hk/en-data/api/3/action/package_search",params={"q":q,"rows":12},headers=UA,timeout=60).json()
    print(f"-- q={q} total={j['result']['count']}")
    for p in j["result"]["results"][:12]:
        if "tablechart" in p["name"] or "death" in p["name"].lower():
            print("    ", p["name"], "|", p["title"][:95])
