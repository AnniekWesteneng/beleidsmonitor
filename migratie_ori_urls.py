"""Eenmalig: repareer de bron-links van bestaande Open Raadsinformatie-signalen.

De links wezen naar de directe document-URL (original_url), die bij notubiz
(o.a. Den Haag) een 400 geeft. We vervangen ze door de betrouwbare resolve-URL.
Kost geen tokens — alleen ORI bevragen.

Draaien:  python migratie_ori_urls.py
"""
import json
import time
import sqlite3

import requests

from config import GEMEENTEN, ZOEKTERMEN
from bronnen.open_raadsinformatie import _index_voor, BASE, HEADERS
from database import DB_PATH

# 1. Bouw een map original_url -> resolve_url door ORI opnieuw te bevragen.
mapping = {}
for gemeente in GEMEENTEN:
    index = _index_voor(gemeente)
    print(f"ORI bevragen: {gemeente} ({index})", flush=True)
    for term in ZOEKTERMEN:
        body = {
            "size": 10,
            "query": {"bool": {"must": [{"simple_query_string": {
                "fields": ["text", "title", "description", "name"],
                "default_operator": "and", "query": term}}]}},
            "_source": ["url", "original_url"],
        }
        try:
            r = requests.post(f"{BASE}/{index}/_search", headers=HEADERS,
                              data=json.dumps(body), timeout=40)
            for h in r.json().get("hits", {}).get("hits", []):
                s = h.get("_source", {})
                ou, ru = s.get("original_url"), s.get("url")
                if ou and ru:
                    mapping[ou] = ru
        except Exception as e:
            print(f"   fout bij '{term}': {type(e).__name__}")
        time.sleep(0.2)

print(f"\n{len(mapping)} document-links opgehaald. Database bijwerken...")

# 2. Werk de bestaande rijen bij.
conn = sqlite3.connect(DB_PATH)
bij = 0
for ou, ru in mapping.items():
    cur = conn.execute(
        "UPDATE signalen SET url = ? WHERE url = ? AND bron = 'Open Raadsinformatie'",
        (ru, ou))
    bij += cur.rowcount
conn.commit()

rest = conn.execute(
    "SELECT count(*) FROM signalen WHERE bron='Open Raadsinformatie' "
    "AND url LIKE '%notubiz%'").fetchone()[0]
print(f"Klaar. {bij} rijen bijgewerkt. Nog {rest} notubiz-links over (niet teruggevonden).")
