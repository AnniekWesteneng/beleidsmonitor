"""Verken of provincienamen als creator werken in de SRU-API."""
import time
import requests
from bs4 import BeautifulSoup

SRU = "https://repository.overheid.nl/sru"
HEADERS = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1"}


def get(query):
    params = {"operation": "searchRetrieve", "version": "2.0",
              "maximumRecords": "3", "query": query}
    for p in range(1, 5):
        r = requests.get(SRU, params=params, headers=HEADERS, timeout=60)
        if "Dienst tijdelijk niet beschikbaar" in r.text or r.status_code >= 500:
            time.sleep(8 * p); continue
        return r.text
    return None


for prov in ["Zuid-Holland", "Utrecht", "Flevoland"]:
    q = (f'(dt.creator="{prov}") and (cql.textAndIndexes="bedrijventerrein") '
         f'and (dt.date>="2022-01-01") sortBy dt.date/sort.descending')
    xml = get(q)
    s = BeautifulSoup(xml, "lxml-xml")
    n = s.find("numberOfRecords")
    print(f"\n### Provincie {prov}: numberOfRecords = {n.text if n else '?'}")
    for rec in s.find_all("record")[:3]:
        c = rec.find("creator"); p = rec.find("publicatienaam"); t = rec.find("title")
        print(f"   creator={c.text if c else '-'!r} | pub={p.text if p else '-'!r} | {t.text[:50] if t else '-'}")
    time.sleep(3)
