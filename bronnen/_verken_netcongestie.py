"""Achterhaal de ECHTE kleurformule (Arcade) van de capaciteitskaart."""
import json
import requests

HEADERS = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1"}
SERVICE = ("https://services.arcgis.com/nSZVuSZjHpEZZbRo/arcgis/rest/services/"
           "Capaciteitskaart_elektriciteitsnet_v2_afname/FeatureServer")

lyr = requests.get(f"{SERVICE}/0?f=json", headers=HEADERS, timeout=30).json()
r = lyr.get("drawingInfo", {}).get("renderer", {})

print("=== Renderer ===")
print("type:", r.get("type"))
print("field1:", r.get("field1"), "| field:", r.get("field"))
print("\n=== valueExpression (Arcade-formule) ===")
print(r.get("valueExpression"))

print("\n=== uniqueValueInfos (categorie -> kleur) ===")
for uv in r.get("uniqueValueInfos", []):
    kleur = uv.get("symbol", {}).get("color")
    print(f"  value={uv.get('value')!r} | RGBA={kleur}")

# Voorbeeldrecords met alle relevante velden, voor Utrecht.
print("\n=== Utrecht-records (ruwe velden) ===")
q = requests.get(f"{SERVICE}/0/query",
                 params={"where": "voedingsgebied_naam LIKE '%Utrecht%'",
                         "outFields": "*", "f": "json", "returnGeometry": "false"},
                 headers=HEADERS, timeout=30).json()
for f in q.get("features", []):
    print("  ", json.dumps(f.get("attributes", {}), ensure_ascii=False))
