import requests, json
UA={"user-agent":"Mozilla/5.0"}
B="https://api.data.gov.hk/v1/historical-archive"
print("### list-files (what URLs are archived)")
r=requests.get(f"{B}/list-files",params={"start":"20250101","end":"20250110"},headers=UA,timeout=180)
print(r.status_code, len(r.text))
try:
    j=r.json(); files=j.get("files",[])
    print("n:",len(files)); print(json.dumps(files[:6],indent=1))
    keys=set()
    for f in files: keys.add(f.get("url","").split("/")[2] if "/" in f.get("url","") else "?")
    print("hosts:", sorted(keys)[:40])
    fehd=[f for f in files if "fehd" in f.get("url","").lower()]
    print("fehd files sample:", json.dumps(fehd[:5],indent=1))
except Exception as e:
    print(r.text[:800])
