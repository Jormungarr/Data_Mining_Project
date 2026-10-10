"""方案二可行性實測：酒店房間入住率 × 食肆牌照 × 2021人口普查（+ 補充資料）"""
import pandas as pd, numpy as np, pathlib, json, re, collections
from lxml import etree
D=pathlib.Path("data"); out=pathlib.Path("out"); out.mkdir(exist_ok=True)
pd.set_option("display.width",240)

print("="*95); print("方案二 TEST — 酒店入住率 × 食肆牌照 × 2021人口普查"); print("="*95)

# ---------- 1. 酒店入住率 ----------
h=pd.read_csv(D/"f2_hotel/hotel_room_occupancy_rate_monthly_by_district_en.csv")
hy=pd.read_csv(D/"f2_hotel/hotel_room_occupancy_rate_monthly_en.csv")
print("\n[1] 酒店房間入住率")
print("  整體月度: rows=%d  %s → %s" % (len(hy), hy.iloc[0,0], hy.iloc[-1,0]))
print("  分區月度: rows=%d  cols=%d" % (len(h), len(h.columns)))
print("  分區清單:")
for c in h.columns[1:]: print("     -", c.strip())
print("  → 時間鍵 = Year-Month (YYYYMM)，粒度=月，覆蓋 2021-08 ~ 2026-07（近 5 年）")
print("  → 空間鍵 = 8 個『旅遊區』分組，**不是 18 個區議會分區**")

# ---------- 2. 食肆牌照 ----------
print("\n[2] 食肆牌照 (FEHD Restaurant licences)")
root=etree.parse(str(D/"f2_licence/LP_Restaurants_EN.XML")).getroot()
lps=root.findall(".//LP")
tags=collections.Counter(c.tag for lp in lps for c in lp)
print("  牌照筆數:", len(lps))
print("  每筆欄位:", dict(tags))
print("  GENERATION_DATE:", root.findtext("GENERATION_DATE"))
print("  日期類欄位:", [t for t in tags if "DATE" in t], " → 只有到期日 EXPDATE，**沒有發牌日期 ISSUE DATE**")
dists={c.get("ID"):c.text for c in root.findall(".//DIST_CODE/CODE")}
print("  分區數:", len(dists), " →", list(dists.values()))
cnt=pd.Series(collections.Counter(lp.findtext("DIST") for lp in lps)).sort_index()
print("  各區持牌食肆數（2026-10 快照）:"); print("   ", {dists.get(k,k):int(v) for k,v in cnt.items()})
exp=pd.Series([lp.findtext("EXPDATE") for lp in lps]).value_counts().sort_index()
print("  EXPDATE 分佈（前/後 3）:", dict(exp.head(3)), "...", dict(exp.tail(3)), " 不同到期日數:", exp.size)
print("  → 這是**單一時點快照**：可以算『各區持牌食肆存量』，但無法還原『每月新增』")

# ---------- 3. 人口普查 ----------
print("\n[3] 2021人口普查（按區議會分區）")
cen=pd.read_csv(D/"f1_census/DC_21C.CSV")
dc=cen[cen.iloc[:,2].astype(str).str.match(r"^(?!Name of)[A-Za-z]")].copy()
print("  表 shape:", cen.shape, " 分區列:", len(dc))
print("  分區（英文）:", sorted(dc.iloc[:,2].dropna().unique()))
print("  → 時間鍵 = **2021 年單一橫截面**（普查），在月度面板中只能是『時間不變的協變量』")

# ---------- 4. 補充：季度食肆收益（有時間序列） ----------
print("\n[4] 補充：餐飲業收益（C&SD 625-68003）— 這是唯一『有時間序列的食肆活動』指標")
rj=json.loads((D/"f2_rest/625-68003.json").read_text())
r=pd.DataFrame(rj["dataSet"])
rq=r[r.freq=="Q"].copy(); rq["grp"]=rq["REST_GRPDesc"].str.strip()
rq["q"]=rq.period.astype(str).str[:4]+"Q"+(((rq.period.astype(str).str[4:6].astype(int)-1)//3)+1).astype(str)
print("  季度資料 期數:", rq.period.nunique(), " 範圍:", rq.period.min(),"→",rq.period.max())
print("  分組:", sorted(rq.grp.unique()))
piv=rq[rq.sv=="VAL_RR"].pivot_table(index="q",columns="grp",values="figure")
piv.index.name="period"
print(piv.tail(4).to_string())
print("  → 季度粒度，與酒店的『月』粒度不一致，需降頻（月→季）後才能對齊")

print("\n[5] 補充：訪港旅客（C&SD 650-80001）月度")
vj=json.loads((D/"f2_visitor/650-80001.json").read_text())
v=pd.DataFrame(vj["dataSet"]); vm=v[v.freq=="M"]
print("  月度期數:", vm.period.nunique(), "範圍:", vm.period.min(),"→",vm.period.max())

# ---------- 6. 拼接模擬 ----------
print("\n[6] 拼接模擬")
h2=h.copy(); h2["ym"]=h2["Year-Month"].astype(str); h2["q"]=h2.ym.str[:4]+"Q"+(((h2.ym.str[4:6].astype(int)-1)//3)+1).astype(str)
hot_q=h2.groupby("q")[[c for c in h.columns if c!= "Year-Month"]].mean()
j1=hot_q.join(piv,how="inner")
print("  酒店(月→季平均) ⋈ 餐飲收益(季) 內連接: %d 季 × %d 欄" % j1.shape[:2])
j2=hot_q.join(piv,how="outer")
print("  外連接後缺值數:", int(j2.isna().sum().sum()), " → 重疊期間:", sorted(set(hot_q.index)&set(piv.index))[:3],"...")
print("  可對齊的季度數 =", len(j1), "（酒店只有 5 年 → 約 20 季）")
DC2HOT={"Central / Western":"Central/Western","Wan Chai":"Wan Chai","Eastern & Southern Hong Kong":"Eastern/Southern",
        "Tsim Sha Tsui":"Yau Tsim Mong","Yau Ma Tei / Mong Kok ":"Yau Tsim Mong","other Kowloon":"Sham Shui Po/Kwun Tong",
        "New Territories":"NT districts","Island":"Islands"}
print("  酒店旅遊區 → 18 區 對照是多對一且不完整：")
for k,vv in DC2HOT.items(): print(f"     {k.strip():32s} -> {vv}")
print("  → 人口普查協變量在時間上完全沒有變異（2021 一個值）")

pd.DataFrame({"hotel_q":hot_q.iloc[:,0]}).join(piv,how="inner").to_csv(out/"f2_joined_hotel_restaurant_quarterly.csv")
print("\n[輸出] out/f2_joined_hotel_restaurant_quarterly.csv")

print("\n[結論] 方案二：**部分成立，但需改設計**")
print("   ✔ 酒店入住率：月度 + 分區，2021-08 起，可用")
print("   ✘ 食肆牌照：只有快照、沒有發牌日期 →『每月新增持牌食肆』做不出來")
print("     （歷史存檔 API api.data.gov.hk/v1/historical-archive 對該 URL 回傳 0 個版本，無法回溯）")
print("   ✔ 替代：用 C&SD 625-68003 餐飲業收益（季度）當『社區商業活力』代理變量")
print("   △ 地理鍵：酒店旅遊區 ≠ 18 區議會分區，需人工對照且多對一")
print("   △ 人口普查只有 2021 一個橫截面 → 只能當時間不變協變量（固定效應/交互項）")
