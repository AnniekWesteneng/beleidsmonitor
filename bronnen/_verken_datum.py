"""Verken of de SRU-API een datumfilter ondersteunt in CQL."""
import time
import requests
from bs4 import BeautifulSoup

SRU = "https://repository.overheid.nl/sru"
HEADERS = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1"}


def get(query, mr=3):
    params = {"operation": "searchRetrieve", "version": "2.0",
              "maximumRecords": str(mr), "query": query}
    for p in range(1, 5):
        r = requests.get(SRU, params=params, headers=HEADERS, timeout=60)
        if "Dienst tijdelijk niet beschikbaar" in r.text or r.status_code >= 500:
            print(f"  throttle, wacht {8*p}s..."); time.sleep(8 * p); continue
        return r.text
    return None


def toon(label, query):
    print(f"\n##### {label}\n  {query}")
    xml = get(query)
    if not xml:
        print("  geen respons"); return
    s = BeautifulSoup(xml, "lxml-xml")
    n = s.find("numberOfRecords")
    print(f"  numberOfRecords: {n.text if n else '??'}")
    for rec in s.find_all("record")[:3]:
        d = rec.find("date"); t = rec.find("title")
        print(f"   - datum={d.text if d else '-'} | {t.text[:45] if t else '-'}")
    time.sleep(3)


# Basis (geen datumfilter) ter referentie
toon("geen datumfilter", '(dt.creator="Almere") and (cql.textAndIndexes="bedrijventerrein")')
# Datumfilter-kandidaten
toon("dt.date >= 2023-01-01",
     '(dt.creator="Almere") and (cql.textAndIndexes="bedrijventerrein") and (dt.date>="2023-01-01")')
toon("dt.modified >= 2023-01-01",
     '(dt.creator="Almere") and (cql.textAndIndexes="bedrijventerrein") and (dt.modified>="2023-01-01")')
# Sorteren op datum aflopend (nieuwste eerst)
toon("sortBy dt.date aflopend",
     '(dt.creator="Almere") and (cql.textAndIndexes="bedrijventerrein") sortBy dt.date/sort.descending')
