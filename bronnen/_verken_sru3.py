"""Verkenning 3 (robuust + beleefd):
1. Hoe heten Den Haag / Almere in de data (creator)?
2. Hoe filteren we Gemeenteblad eruit (vs Provinciaal blad)?
Met pauzes tussen aanroepen en retry-met-backoff bij "Dienst tijdelijk niet beschikbaar".
"""
import time
import requests
from bs4 import BeautifulSoup

SRU_ENDPOINT = "https://repository.overheid.nl/sru"


def sru_get(query, max_records=3, pogingen=4):
    params = {
        "operation": "searchRetrieve", "version": "2.0",
        "maximumRecords": str(max_records), "query": query,
    }
    for poging in range(1, pogingen + 1):
        try:
            resp = requests.get(SRU_ENDPOINT, params=params, timeout=60)
        except Exception as e:
            print(f"  (poging {poging}) netwerkfout: {type(e).__name__}")
            time.sleep(5 * poging)
            continue
        if "Dienst tijdelijk niet beschikbaar" in resp.text or resp.status_code >= 500:
            wacht = 8 * poging
            print(f"  (poging {poging}) dienst niet beschikbaar, wacht {wacht}s...")
            time.sleep(wacht)
            continue
        return resp.text
    return None


def query_info(label, query):
    print(f"\n##### {label}")
    print(f"  query: {query}")
    xml = sru_get(query)
    if xml is None:
        print("  -> Bleef onbeschikbaar na alle pogingen.")
        return
    soup = BeautifulSoup(xml, "lxml-xml")
    aantal = soup.find("numberOfRecords")
    print(f"  numberOfRecords: {aantal.text if aantal else '??'}")
    for rec in soup.find_all("record")[:3]:
        c = rec.find("creator"); p = rec.find("publicatienaam"); t = rec.find("title")
        print(f"   - creator={c.text if c else '-'!r} | pub={p.text if p else '-'!r} | titel={(t.text[:55] if t else '-')!r}")
    time.sleep(3)  # beleefde pauze tussen queries


# Wacht eerst even zodat de dienst kan herstellen.
print("Even 20s wachten zodat de dienst herstelt...")
time.sleep(20)

TESTS = [
    ("Utrecht (bekend werkend)", '(dt.creator="Utrecht") and (cql.textAndIndexes="bedrijventerrein")'),
    ("Den Haag", '(dt.creator="Den Haag") and (cql.textAndIndexes="bedrijventerrein")'),
    ("'s-Gravenhage", '(dt.creator="\'s-Gravenhage") and (cql.textAndIndexes="bedrijventerrein")'),
    ("Almere", '(dt.creator="Almere") and (cql.textAndIndexes="bedrijventerrein")'),
]
for label, query in TESTS:
    query_info(label, query)
