import json, pathlib
o=json.loads(pathlib.Path("data/f3_ha/daily_services_en.json").read_text())
print("type:",type(o))
if isinstance(o,dict): print("keys:",list(o)[:20])
s=json.dumps(o,ensure_ascii=False,indent=1)
print(s[:2500])
