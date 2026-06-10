"""Verkenning 2: hoe filteren we op GEMEENTE?

We proberen een paar kandidaat-CQL-velden en printen per record de
creator + publicatienaam + titel, zodat we zien wat werkt.
"""
import requests
from bs4 import BeautifulSoup

SRU_ENDPOINT = "https://repository.overheid.nl/sru"

KANDIDAAT_QUERIES = {
    "dt.creator gemeente Utrecht": '(c.product-area==officielepublicaties) and (dt.creator=="gemeente Utrecht") and (cql.textAndIndexes="bedrijventerrein")',
    "dt.creator Utrecht": '(c.product-area==officielepublicaties) and (dt.creator="Utrecht") and (cql.textAndIndexes="bedrijventerrein")',
    "creator Utrecht": '(c.product-area==officielepublicaties) and (creator="Utrecht") and (cql.textAndIndexes="bedrijventerrein")',
    "publicatienaam Gemeenteblad + tekst Utrecht": '(c.product-area==officielepublicaties) and (w.publicatienaam=="Gemeenteblad") and (cql.textAndIndexes="bedrijventerrein Utrecht")',
}


def probeer(naam, query):
    params = {
        "operation": "searchRetrieve",
        "version": "2.0",
        "maximumRecords": "3",
        "query": query,
    }
    print(f"\n##### {naam}")
    print(f"query: {query}")
    try:
        resp = requests.get(SRU_ENDPOINT, params=params, timeout=30)
    except Exception as e:
        print("  FOUT:", e)
        return
    soup = BeautifulSoup(resp.text, "lxml-xml")
    diag = soup.find("diag:diagnostic") or soup.find("diagnostic")
    aantal = soup.find("numberOfRecords")
    print("  numberOfRecords:", aantal.text if aantal else "?")
    if diag:
        print("  DIAGNOSTIC:", diag.get_text(" ", strip=True)[:300])
    for rec in soup.find_all("record")[:3]:
        creator = rec.find("creator")
        pubnaam = rec.find("publicatienaam")
        titel = rec.find("title")
        print(f"   - creator={creator.text if creator else '-'!r} | "
              f"pub={pubnaam.text if pubnaam else '-'!r} | "
              f"titel={(titel.text[:60] if titel else '-')!r}")


for naam, query in KANDIDAAT_QUERIES.items():
    probeer(naam, query)
