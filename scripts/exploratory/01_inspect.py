import pathlib, json, zipfile, io
D = pathlib.Path("data")

def head(p, n=6, enc=None):
    print(f"\n===== {p} ({p.stat().st_size:,} bytes)")
    b = p.read_bytes()
    for e in ([enc] if enc else ["utf-8-sig","utf-8","utf-16","latin-1"]):
        try:
            t = b.decode(e); print(f"  [enc={e}]"); break
        except Exception: continue
    lines = t.splitlines()
    for l in lines[:n]: print("   |", l[:220])
    print(f"   ... total lines = {len(lines)}")

for f in ["f1_traffic/am_peak_journey_time_on_hong_kong_island_2024.csv",
          "f1_aqhi/202401_Eng.csv",
          "f2_hotel/hotel_room_occupancy_rate_monthly_by_district_en.csv",
          "f2_hotel/hotel_room_occupancy_rate_monthly_en.csv",
          "f3_flu/flux_data.csv",
          "f3_death/deaths_by_leading_cause_en.csv"]:
    head(D/f)

print("\n===== f2_licence/LP_Restaurants_EN.XML (first 3000 chars)")
print((D/"f2_licence/LP_Restaurants_EN.XML").read_text("utf-8","replace")[:3000])

print("\n===== f1_census/DC_21C.zip contents")
z = zipfile.ZipFile(D/"f1_census/DC_21C.zip")
for i in z.infolist()[:60]: print("   ", i.filename, i.file_size)
print("   total entries:", len(z.infolist()))

for j in ["f3_death/monthly_deaths_by_sex_115-01022A.json","f3_death/deaths_by_sex_age_115-01022.json"]:
    o = json.loads((D/j).read_text())
    print(f"\n===== {j}")
    print("  top keys:", list(o)[:20])
    s = json.dumps(o)[:1500]
    print("  ", s)
