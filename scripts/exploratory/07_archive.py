import requests, json
UA={"user-agent":"Mozilla/5.0"}
B="https://api.data.gov.hk/v1/historical-archive"
tests=[
 "https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML",
 "https://www.fehd.gov.hk/tc_chi/licensing/license/text/LP_Restaurants_TC.XML",
 "https://www.tourism.gov.hk/datagovhk/hotelroomoccupancy/hotel_room_occupancy_rate_monthly_by_district_en.csv",
 "https://www.aqhi.gov.hk/epd/ddata/html/history/2024/202401_Eng.csv",
 "https://www.chp.gov.hk/files/misc/flux_data.csv",
]
for u in tests:
    r=requests.get(f"{B}/list-file-versions",params={"url":u,"start":"20210101","end":"20261009"},headers=UA,timeout=180)
    try:
        vs=r.json().get("versions",[])
    except Exception: vs=None
    print(f"{len(vs) if vs is not None else 'ERR':>4} versions  {u}")
    if vs: print("      first:",vs[0],"last:",vs[-1])

print("\n### try dataset-id filter on list-files")
for extra in [{"dataset-id":"hk-fehd-fehdlmis-restaurant-licences"},{"url":"https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML"}]:
    p={"start":"20250101","end":"20250110"}; p.update(extra)
    r=requests.get(f"{B}/list-files",params=p,headers=UA,timeout=180)
    try:
        j=r.json(); print(extra, "->", len(j.get("files",[])), json.dumps(j.get("files",[])[:1],indent=1)[:400])
    except Exception: print(extra,"->",r.text[:300])
