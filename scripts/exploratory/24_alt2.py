import requests,re
UA={"user-agent":"Mozilla/5.0"}
for i in ["hk-td-sm_4-traffic-data-strategic-major-roads","hk-td-sm_5-annual-traffic-census-survey-data",
          "hk-td-sm_1-traffic-speed-map","hk-td-tis_28-traffic-data-tdas","hk-td-tis_32-traffic-data-aivas",
          "hk-td-tis_33-traffic-data-traffic-detectors-installed-at-smart-lampposts"]:
    try:
        p=requests.get(f"https://data.gov.hk/en-data/api/3/action/package_show?id={i}",headers=UA,timeout=60).json()["result"]
    except Exception as e:
        print("FAIL",i,e); continue
    print("="*80); print(p["title"]); print("  NOTES:",(p.get("notes") or "").replace("\n"," ")[:300])
    for r in p["resources"][:5]: print("   R:",r["name"][:90],"|",r["format"],"|",r["url"])
    print("   n_resources:",len(p["resources"]))
