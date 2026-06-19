"""Laag 1 — Bron 2: Open Raadsinformatie (Open State Foundation).

Raadsstukken (agendapunten, nota's, rapporten) van gemeenteraden. Vangt beleid
op dat vaak vóór officiële publicatie al in de raad besproken wordt.

Endpoint: https://api.openraadsinformatie.nl/v1/elastic  (Elasticsearch)

Geverifieerd tegen de echte API (zie _verken_ori.py):
- Elke gemeente heeft een eigen index: ori_<gemeente>_<tijdstempel>.
  Filteren gaat via de wildcard in de URL, bv. ori_utrecht*/_search.
- Den Haag = ori_den_haag*  (met underscore).
- Volledige tekst zit in het veld 'text' (een lijst met één string per pagina).
- Datum = last_discussed_at (ISO). Titel = name. Bron-URL = original_url/url.

Eenvormige interface met bron 1:
  haal(gemeente, zoekterm, max_resultaten) -> list[dict]  (metadata + tekst)
  vul_tekst(doc) -> str
  BRON_NAAM
"""
import json
import sys
import time
from pathlib import Path

import requests

# Maak imports werkend of het script nu vanuit de root of vanuit bronnen/ draait.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import VANAF_JAAR  # noqa: E402

BASE = "https://api.openraadsinformatie.nl/v1/elastic"
BRON_NAAM = "Open Raadsinformatie"
HEADERS = {
    "User-Agent": "Beleidsmonitor-TodayDevelopment/0.1 (afstudeerproject)",
    "Content-Type": "application/json",
}

# Uitzonderingen op de standaard-indexnaam (slug). Onze 3 gemeenten volgen
# de standaardregel, maar hier kun je afwijkende namen toevoegen.
INDEX_ALIASSEN: dict[str, str] = {
    # Den Bosch heet in ORI 'ori_den_bosch' (niet 's-hertogenbosch').
    "'s-Hertogenbosch": "ori_den_bosch",
}


def _index_voor(gemeente: str) -> str:
    if gemeente in INDEX_ALIASSEN:
        basis = INDEX_ALIASSEN[gemeente]
    else:
        slug = gemeente.lower().replace(" ", "_").replace("'", "")
        basis = f"ori_{slug}"
    return basis + "*"  # wildcard vangt de tijdstempel-suffix


def _tekst_uit_hit(src: dict) -> str:
    """Het 'text'-veld is een lijst met één string per pagina; plak samen."""
    tekst = src.get("text")
    if isinstance(tekst, list):
        return " ".join(t for t in tekst if t)
    if isinstance(tekst, str):
        return tekst
    md = src.get("md_text")
    if isinstance(md, list):
        return " ".join(t for t in md if t)
    return md or ""


def haal(gemeente: str, zoekterm: str, max_resultaten: int = 20,
         pogingen: int = 3) -> list[dict]:
    """Zoek raadsstukken voor een gemeente + zoekterm, nieuwste eerst,
    vanaf VANAF_JAAR. De tekst zit al in de respons."""
    index = _index_voor(gemeente)
    body = {
        "size": max_resultaten,
        "query": {
            "bool": {
                "must": [{
                    "simple_query_string": {
                        "fields": ["text", "title", "description", "name"],
                        "default_operator": "and",
                        "query": zoekterm,
                    }
                }],
                "filter": {
                    "range": {"last_discussed_at": {"gte": f"{VANAF_JAAR}-01-01"}}
                },
            }
        },
        "sort": [{"last_discussed_at": {"order": "desc"}}],
    }

    url = f"{BASE}/{index}/_search"
    data = None
    for poging in range(1, pogingen + 1):
        try:
            resp = requests.post(url, headers=HEADERS, data=json.dumps(body), timeout=60)
        except Exception as e:
            print(f"    ORI netwerkfout ({type(e).__name__}), wacht {5*poging}s...")
            time.sleep(5 * poging)
            continue
        if resp.status_code == 404:
            # Geen index voor deze gemeente (bv. doet niet mee aan ORI).
            return []
        if resp.status_code >= 500:
            print(f"    ORI serverfout {resp.status_code}, wacht {5*poging}s...")
            time.sleep(5 * poging)
            continue
        try:
            data = resp.json()
        except Exception:
            return []
        break
    if not data:
        return []

    resultaten = []
    for hit in data.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        datum = (src.get("last_discussed_at") or "")[:10]  # alleen JJJJ-MM-DD
        resultaten.append({
            "gemeente": gemeente,
            "titel": src.get("title") or src.get("name") or "(zonder titel)",
            "documenttype": "Raadsstuk",
            "bron": BRON_NAAM,
            "datum": datum,
            # De resolve-URL opent het document betrouwbaar (PDF). De directe
            # original_url geeft bij sommige systemen, zoals notubiz, een 400.
            "url": src.get("url") or src.get("original_url") or "",
            "tekst": _tekst_uit_hit(src),
        })
    return resultaten


def vul_tekst(doc: dict) -> str:
    """Tekst zit al in de zoekrespons; gewoon teruggeven (eenvormige interface)."""
    return doc.get("tekst", "")


if __name__ == "__main__":
    print("Test: Utrecht / bedrijventerrein (eerste 3 raadsstukken)\n")
    docs = haal("Utrecht", "bedrijventerrein", max_resultaten=3)
    print(f"Aantal: {len(docs)}\n")
    for i, d in enumerate(docs, 1):
        print(f"--- {i} ---")
        print(f"  Titel : {d['titel']}")
        print(f"  Datum : {d['datum']}")
        print(f"  URL   : {d['url']}")
        print(f"  Tekst : {len(d['tekst'])} tekens | {d['tekst'][:150]!r}\n")
