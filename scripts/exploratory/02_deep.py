import pandas as pd, json, pathlib, zipfile, re
pd.set_option("display.width",250); pd.set_option("display.max_columns",50)
D=pathlib.Path("data")

print("########## 1. TD journey time full structure")
t=pd.read_csv(D/"f1_traffic/am_peak_journey_time_on_hong_kong_island_2024.csv",header=None,skiprows=3)
print(t.head(12).to_string())
print("shape",t.shape)
print("unique col4/col5 sample:", t[4].dropna().unique()[:10], t[5].dropna().unique()[:10])
print("nonnull counts per col:", t.notna().sum().to_dict())

print("\n########## 2. AQHI structure")
a=pd.read_csv(D/"f1_aqhi/202401_Eng.csv",skiprows=6)
print(a.head(4).to_string())
print("shape",a.shape); print("cols:",list(a.columns)[:30])
print("tail:"); print(a.tail(3).to_string())
