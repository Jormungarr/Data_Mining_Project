"""HA 数据集完整剖析"""
import pandas as pd, numpy as np, pathlib, json
D=pathlib.Path("data"); pd.set_option("display.width",250); pd.set_option("display.max_rows",300)
ha=pd.DataFrame(json.loads((D/"f3_ha/daily_services_en.json").read_text()))
ha["date"]=pd.to_datetime(ha.date)

print("="*95); print("HA「Key Statistics during Service Demand Surge」完整結構"); print("="*95)
print("\n[1] 規模")
print("  總列數:", len(ha))
print("  欄位:", list(ha.columns))
print("  surge_year 值:", sorted(ha.surge_year.unique()))
print("  cluster 值 (%d):"%ha.cluster.nunique()); [print("     -",c) for c in sorted(ha.cluster.unique())]
print("  hospital 值 (%d):"%ha.hospital.nunique())
print("  HA Overall 列數:", (ha.cluster=='HA Overall').sum(), " → 每個日期一列彙總")

print("\n[2] 每個 surge_year 的實際覆蓋")
g=ha[ha.cluster=="HA Overall"].groupby("surge_year").agg(
    n_days=("date","nunique"), first=("date","min"), last=("date","max"))
g["span_days"]=(g["last"]-g["first"]).dt.days+1
g["gaps"]=g["span_days"]-g["n_days"]
print(g.to_string())

print("\n[3] 日期是否連續？（HA Overall）")
d=sorted(ha[ha.cluster=="HA Overall"].date.unique())
d=pd.Series(pd.to_datetime(d))
diff=d.diff().dt.days
print("  實際天數:", len(d), " 跨度:", (d.max()-d.min()).days+1, "天 → 缺口", (d.max()-d.min()).days+1-len(d), "天")
print("  相鄰日差分佈:"); print(diff.value_counts().sort_index().to_string())
print("\n  缺口的具體位置（>1 天）:")
br=pd.DataFrame({"date":d,"gap":diff})
print(br[br.gap>1].to_string())
