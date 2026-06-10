"""Pipeline: zet alle lagen aan elkaar — ophalen -> classificeren -> opslaan.

Loopt over ALLE bronnen in BRONNEN. Elke bron biedt dezelfde interface:
    bron.BRON_NAAM
    bron.haal(gemeente, zoekterm, max_resultaten) -> list[dict] (metadata)
    bron.vul_tekst(doc) -> str

Per bron/gemeente/zoekterm:
  1. Metadata ophalen (snel).
  2. Al verwerkte URLs overslaan (bespaart API-kosten).
  3. Alleen voor nieuwe documenten: tekst ophalen + classificeren.
  4. Relevante signalen opslaan.

Draaien:  python pipeline.py
"""
from config import GEMEENTEN, ZOEKTERMEN, PROVINCIES
from bronnen import officiele_bekendmakingen, open_raadsinformatie
from classificeer import classificeer
from database import init_db, sla_op, url_bestaat

# Alle gekoppelde bronnen. Een nieuwe bron toevoegen = hier in de lijst zetten.
BRONNEN = [officiele_bekendmakingen, open_raadsinformatie]


def run(gemeenten=None, zoektermen=None, max_per_term: int = 10, provincies=None):
    gemeenten = gemeenten or GEMEENTEN
    zoektermen = zoektermen or ZOEKTERMEN
    provincies = provincies if provincies is not None else PROVINCIES
    conn = init_db()
    nieuw = 0
    for bron in BRONNEN:
        # Gebieden = gemeenten, plus provincies als de bron dat ondersteunt.
        gebieden = list(gemeenten)
        if getattr(bron, "ONDERSTEUNT_PROVINCIES", False):
            gebieden += list(provincies)
        for gemeente in gebieden:
            for term in zoektermen:
                print(f"[{bron.BRON_NAAM}] {gemeente} / {term}", flush=True)
                docs = bron.haal(gemeente, term, max_resultaten=max_per_term)
                for doc in docs:
                    if url_bestaat(conn, doc["url"]):
                        continue  # al verwerkt: bespaar API-kosten
                    tekst = bron.vul_tekst(doc)
                    if not tekst:
                        continue  # geen tekst: overslaan
                    # Eén document kan meerdere signalen opleveren.
                    signalen = classificeer(doc["titel"], tekst, zoekterm=term)
                    for signaal in signalen:
                        sla_op(conn, {**doc, **signaal})
                        nieuw += 1
                    if signalen:
                        inds = ", ".join(
                            f"{s['indicator_id']}:{s['classificatie']}" for s in signalen
                        )
                        print(f"  + {doc['titel'][:55]} -> {inds}", flush=True)
    totaal = conn.execute("SELECT count(*) FROM signalen").fetchone()[0]
    print(f"\nKlaar. {nieuw} nieuwe signalen. Totaal in DB: {totaal}")


if __name__ == "__main__":
    run()
