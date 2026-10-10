import pandas as pd

df = pd.read_csv("data/processed/panel_hospital_week.csv")

df.shape                                   # (2448, 34) - 2448 hospital-weeks, 34 columns
df.head()                                  # what does a row look like?
df.dtypes                                  # numeric vs text columns
df.isna().mean().sort_values(ascending=False)   # which columns have gaps?

# One value per week, shared by all 17 hospitals:
df.groupby("week_end")["ILI_PMP"].nunique().max()      # -> 1

# Weekly averages over all hospitals, for a first look at the time pattern:
weekly = df.groupby("week_end")[["ae_first_attend", "ILI_PMP"]].mean()
weekly.plot(subplots=True, figsize=(11, 5))