"""Eenmalig: geef bestaande signalen (zonder relevantiescore) alsnog een score.

Gebruikt de reeds opgeslagen samenvatting/onderbouwing, dus geen dure
her-download van de volledige documenttekst.

Draaien:  python backfill_relevantie.py
"""
from database import init_db
from classificeer import scoor_bestaand


def run():
    conn = init_db()  # zorgt ook dat de kolom 'relevantie' bestaat
    rijen = conn.execute(
        "SELECT id, titel, samenvatting, onderbouwing FROM signalen "
        "WHERE relevantie IS NULL"
    ).fetchall()
    print(f"{len(rijen)} signalen zonder score.")
    bijgewerkt = 0
    for rid, titel, samenvatting, onderbouwing in rijen:
        score = scoor_bestaand(titel or "", samenvatting or "", onderbouwing or "")
        if score is not None:
            conn.execute("UPDATE signalen SET relevantie = ? WHERE id = ?", (score, rid))
            conn.commit()
            bijgewerkt += 1
            print(f"  #{rid} -> {score}/5  | {(titel or '')[:55]}")
        else:
            print(f"  #{rid} -> geen score (fout), overgeslagen")
    print(f"\nKlaar. {bijgewerkt} signalen bijgewerkt.")


if __name__ == "__main__":
    run()
