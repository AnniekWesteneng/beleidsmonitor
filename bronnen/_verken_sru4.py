"""Verkenning 4: hoe halen we de VOLLEDIGE TEKST van een document op?"""
import time
import requests
from bs4 import BeautifulSoup

SRU_ENDPOINT = "https://repository.overheid.nl/sru"


def sru_get(query, max_records=5, pogingen=4):
    params = {"operation": "searchRetrieve", "version": "2.0",
              "maximumRecords": str(max_records), "query": query}
    for poging in range(1, pogingen + 1):
        try:
            resp = requests.get(SRU_ENDPOINT, params=params, timeout=60)
        except Exception as e:
            print(f"  netwerkfout poging {poging}: {type(e).__name__}"); time.sleep(5 * poging); continue
        if "Dienst tijdelijk niet beschikbaar" in resp.text or resp.status_code >= 500:
            print(f"  dienst niet beschikbaar, poging {poging}, wacht..."); time.sleep(8 * poging); continue
        return resp.text
    return None


print("Even 15s wachten...")
time.sleep(15)
xml = sru_get('(dt.creator="Almere") and (cql.textAndIndexes="bedrijventerrein")')
soup = BeautifulSoup(xml, "lxml-xml")

rec = soup.find("record")
enriched = rec.find("enrichedData")
print("=== enrichedData eerste record ===")
print(enriched.prettify()[:1400])

pref = rec.find("preferredUrl")
pref_url = pref.text if pref else None
print("preferredUrl:", pref_url)
print("itemUrl manifestations:")
for it in rec.find_all("itemUrl"):
    print("  ", it.get("manifestation"), "->", it.text)

if pref_url:
    time.sleep(3)
    print(f"\n=== HTML ophalen: {pref_url} ===")
    r = requests.get(pref_url, timeout=60)
    print("status:", r.status_code, "| HTML-lengte:", len(r.text))
    psoup = BeautifulSoup(r.text, "lxml")
    for tag in psoup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    tekst = psoup.get_text(" ", strip=True)
    print("geëxtraheerde tekst-lengte:", len(tekst))
    print("\n--- eerste 800 tekens ---\n", tekst[:800])
