"""Verken de Open Raadsinformatie Elastic-API: indices + veldstructuur."""
import json
import requests

BASE = "https://api.openraadsinformatie.nl/v1/elastic"
HEADERS = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1", "Content-Type": "application/json"}

print("=== 1. Welke indices bestaan (cat/indices)? ===")
try:
    r = requests.get(BASE + "/_cat/indices?format=json&h=index", headers=HEADERS, timeout=30)
    if r.status_code == 200:
        idx = sorted(d["index"] for d in r.json())
        print(f"  {len(idx)} indices. Relevante voor onze gemeenten:")
        for naam in idx:
            if any(g in naam for g in ["utrecht", "almere", "haag", "gravenhage", "den_haag"]):
                print("   -", naam)
    else:
        print("  status:", r.status_code, r.text[:200])
except Exception as e:
    print("  fout:", e)

print("\n=== 2. Zoekopdracht 'bedrijventerrein' in Utrecht (ori_utrecht*) ===")
body = {
    "size": 2,
    "query": {"simple_query_string": {
        "fields": ["text", "title", "description", "name"],
        "query": "bedrijventerrein",
    }},
}
try:
    r = requests.post(BASE + "/ori_utrecht*/_search", headers=HEADERS,
                      data=json.dumps(body), timeout=60)
    print("  status:", r.status_code)
    data = r.json()
    total = data.get("hits", {}).get("total")
    print("  totaal hits:", total)
    for h in data.get("hits", {}).get("hits", [])[:2]:
        src = h.get("_source", {})
        print("\n  --- hit (index:", h.get("_index"), ") ---")
        print("  velden:", list(src.keys()))
        for k in ["title", "name", "description", "last_discussed_at", "url",
                  "@id", "id", "classification", "date"]:
            if k in src:
                print(f"    {k}: {json.dumps(src[k], ensure_ascii=False)[:140]}")
        if "text" in src:
            t = src["text"] or ""
            print(f"    text-lengte: {len(t)} | begin: {t[:120]!r}")
except Exception as e:
    print("  fout:", e)
