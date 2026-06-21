"""Gerichte run: alleen Open Raadsinformatie, één of meer gemeenten.

Houdt runs kort (per gemeente) zodat ze niet worden afgekapt. Dankzij de
dedup (url_bestaat) is herhalen veilig: al verwerkte documenten worden
overgeslagen.

Gebruik:  python run_ori.py "Oss"
          python run_ori.py "Oss" "Eindhoven"
"""
import sys

from config import ZOEKTERMEN
from bronnen import open_raadsinformatie as ori
from classificeer import classificeer
from database import init_db, sla_op, url_bestaat


def run_gemeente(conn, gemeente: str, max_per_term: int = 10) -> int:
    nieuw = 0
    for term in ZOEKTERMEN:
        print(f"[ORI] {gemeente} / {term}", flush=True)
        for doc in ori.haal(gemeente, term, max_resultaten=max_per_term):
            if url_bestaat(conn, doc["url"]):
                continue
            tekst = ori.vul_tekst(doc)
            if not tekst:
                continue
            signalen = classificeer(doc["titel"], tekst, zoekterm=term)
            for signaal in signalen:
                sla_op(conn, {**doc, **signaal})
                nieuw += 1
            if signalen:
                inds = ", ".join(f"{s['indicator_id']}:{s['classificatie']}" for s in signalen)
                print(f"  + {doc['titel'][:55]} -> {inds}", flush=True)
    return nieuw


if __name__ == "__main__":
    gemeenten = sys.argv[1:] or ["Oss", "'s-Hertogenbosch", "Eindhoven", "Helmond"]
    conn = init_db()
    totaal_nieuw = 0
    for g in gemeenten:
        n = run_gemeente(conn, g)
        print(f"== {g}: {n} nieuwe signalen ==", flush=True)
        totaal_nieuw += n
    eind = conn.execute("SELECT count(*) FROM signalen").fetchone()[0]
    print(f"\nKlaar. {totaal_nieuw} nieuwe signalen. Totaal in DB: {eind}")
