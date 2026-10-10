import os, requests, pathlib
UA={"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
targets = {
 "f1_traffic/am_peak_journey_time_on_hong_kong_island_2024.csv":
   "https://www.td.gov.hk/datagovhk_td/car-journey-time-data/resources/am_peak_journey_time_on_hong_kong_island_2024.csv",
 "f1_traffic/am_peak_journey_time_in_kowloon_2024.csv":
   "https://www.td.gov.hk/datagovhk_td/car-journey-time-data/resources/am_peak_journey_time_in_kowloon_2024.csv",
 "f1_aqhi/201401_Eng.csv": "https://www.aqhi.gov.hk/epd/ddata/html/history/2014/201401_Eng.csv",
 "f1_aqhi/202401_Eng.csv": "https://www.aqhi.gov.hk/epd/ddata/html/history/2024/202401_Eng.csv",
 "f1_census/DC_21C.zip": "https://www.census2021.gov.hk/doc/DC_21C.zip",
 "f2_hotel/hotel_room_occupancy_rate_monthly_by_district_en.csv":
   "https://www.tourism.gov.hk/datagovhk/hotelroomoccupancy/hotel_room_occupancy_rate_monthly_by_district_en.csv",
 "f2_hotel/hotel_room_occupancy_rate_monthly_en.csv":
   "https://www.tourism.gov.hk/datagovhk/hotelroomoccupancy/hotel_room_occupancy_rate_monthly_en.csv",
 "f2_licence/LP_Restaurants_EN.XML":
   "https://www.fehd.gov.hk/english/licensing/license/text/LP_Restaurants_EN.XML",
 "f3_flu/flux_data.csv": "https://www.chp.gov.hk/files/misc/flux_data.csv",
 "f3_death/deaths_by_leading_cause_en.csv":
   "https://www.dh.gov.hk/datagovhk/ncdd/Number%20of%20Registered%20Deaths%20by%20Leading%20Cause%20of%20Death,%202001%20to%202024%20(EN).csv",
 "f3_death/monthly_deaths_by_sex_115-01022A.json":
   "https://www.censtatd.gov.hk/api/get.php?id=115-01022A&lang=en&full_series=1",
 "f3_death/deaths_by_sex_age_115-01022.json":
   "https://www.censtatd.gov.hk/api/get.php?id=115-01022&lang=en&full_series=1",
}
for rel,u in targets.items():
    p = pathlib.Path("data")/rel
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(u, headers=UA, timeout=60)
        p.write_bytes(r.content)
        print(f"OK  {r.status_code} {len(r.content):>10,}  {rel}")
    except Exception as e:
        print(f"ERR {rel}: {type(e).__name__}: {e}")
