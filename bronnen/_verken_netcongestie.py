"""Verken legenda + gemeente-koppeling van de capaciteitskaart."""
import json
import requests

HEADERS = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1"}
SERVICE = ("https://services.arcgis.com/nSZVuSZjHpEZZbRo/arcgis/rest/services/"
           "Capaciteitskaart_elektriciteitsnet_v2_afname/FeatureServer")

# 1. Legenda: hoe vertaalt de integer 'afname' naar een kleur/label?
lyr = requests.get(f"{SERVICE}/0?f=json", headers=HEADERS, timeout=30).json()
renderer = lyr.get("drawingInfo", {}).get("renderer", {})
print("=== Renderer / legenda ===")
print("type:", renderer.get("type"), "| veld:", renderer.get("field1") or renderer.get("field"))
for uv in renderer.get("uniqueValueInfos", [])[:12]:
    kleur = uv.get("symbol", {}).get("color")
    print(f"  waarde={uv.get('value')!r:>6} | label={uv.get('label')!r} | RGBA={kleur}")

# 2. Welke voedingsgebieden horen bij onze gemeenten?
print("\n=== Voedingsgebieden per gemeente (naam-match) ===")
for stad in ["Utrecht", "Almere", "Haag", "Gravenhage"]:
    q = requests.get(f"{SERVICE}/0/query",
                     params={"where": f"voedingsgebied_naam LIKE '%{stad}%'",
                             "outFields": "voedingsgebied_naam,afname,opwek,wachtrij_afname,wachtrij_invoeding,RNB",
                             "f": "json", "returnGeometry": "false"},
                     headers=HEADERS, timeout=30).json()
    feats = q.get("features", [])
    print(f"\n  '{stad}': {len(feats)} voedingsgebied(en)")
    for f in feats[:6]:
        a = f["attributes"]
        print(f"     {a['voedingsgebied_naam']!r} | afname={a['afname']} opwek={a['opwek']} "
              f"| wachtrij afname={a['wachtrij_afname']} invoeding={a['wachtrij_invoeding']} | {a['RNB']}")
