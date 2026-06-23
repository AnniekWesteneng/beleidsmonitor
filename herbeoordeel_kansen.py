"""Herbeoordeel bestaande 'kans'-signalen onder de strengere KANS-definitie.

Kernvraag per signaal: is dit een CONCRETE ontwikkelingsmogelijkheid voor Today
(ontwikkelaar van industrieel/logistiek vastgoed)? Zo niet, dan wordt de kans
bijgesteld naar contextafhankelijk of risico, of verwijderd als niet relevant.

Werkt alleen met de OPGESLAGEN velden (titel, samenvatting, onderbouwing, citaat) —
niet met de volledige documenttekst. Dat is een bewuste, goedkope opzet; de vier
foutpatronen (speculatie, loze beleidstaal, transformatie-weg-van-industrie,
infra-voor-wonen) zijn doorgaans al uit de analyse zelf te herkennen.

Resumeerbaar: een kolom 'herbeoordeeld' markeert verwerkte signalen, zodat een
herstart (na de ~20-min-limiet) automatisch verder gaat.

Draaien:  python herbeoordeel_kansen.py
"""
import json

from classificeer import _get_client, MODEL, INDICATOREN, _parse_json_antwoord
from database import init_db

_IND = {i["id"]: i["naam"] for i in INDICATOREN}

PROMPT = """Je beoordeelt streng of een eerder als KANS gelabeld beleidssignaal
écht een CONCRETE ontwikkelingsmogelijkheid is voor Today, ontwikkelaar van
industrieel/logistiek vastgoed.

Het is alleen een KANS als er een aanwijsbare maatregel, ontwikkeling of besluit is
met een aannemelijk, concreet voordeel voor industrieel/logistiek vastgoed.

Het is GEEN kans (kies dan contextafhankelijk, risico of verwijderen) wanneer:
- het algemene, positief klinkende beleidstaal is zonder concrete maatregel;
- de "kans" alleen volgt uit speculatie ("kan betekenen", "zou kunnen", "suggereert",
  "biedt mogelijk ruimte") zonder concrete maatregel → meestal contextafhankelijk;
- het gaat om transformatie/herontwikkeling die de industriële/werkfunctie juist
  WEGNEEMT (naar wonen of gemengd gebruik) → dat is risico of verwijderen, ook als
  de tekst zelf "kansen" noemt;
- het investeringen/voorzieningen betreft (OV, infrastructuur) die primair op wonen
  of stationsgebieden zijn gericht en industrie alleen zijdelings raken → verwijderen
  of contextafhankelijk.

Kies "verwijderen" als het signaal niet werkelijk relevant is voor industrieel
vastgoed. Wees streng maar niet overdreven: een echte, concrete kans blijft een kans.

Antwoord UITSLUITEND met JSON:
{"oordeel": "kans"|"contextafhankelijk"|"risico"|"verwijderen", "reden": "<kort>"}"""


def _herbeoordeel(titel, indicator_id, samenvatting, onderbouwing, citaat):
    inhoud = (
        f"Indicator: {indicator_id} — {_IND.get(indicator_id, '')}\n"
        f"Titel: {titel}\n"
        f"Samenvatting: {samenvatting}\n"
        f"Onderbouwing: {onderbouwing}\n"
        f"Citaat: {citaat}"
    )
    try:
        b = _get_client().messages.create(
            model=MODEL, max_tokens=300,
            system=[{"type": "text", "text": PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": inhoud}],
        )
        data = _parse_json_antwoord(b.content[0].text.strip())
        oordeel = data.get("oordeel")
        if oordeel in {"kans", "contextafhankelijk", "risico", "verwijderen"}:
            return oordeel
    except Exception as e:
        print(f"    fout: {type(e).__name__}: {e}")
    return None  # bij twijfel/fout: niets wijzigen


def main():
    conn = init_db()
    # Migratie: vlag-kolom toevoegen indien nodig.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(signalen)")]
    if "herbeoordeeld" not in cols:
        conn.execute("ALTER TABLE signalen ADD COLUMN herbeoordeeld INTEGER DEFAULT 0")
        conn.commit()

    rijen = conn.execute(
        "SELECT id, titel, indicator_id, samenvatting, onderbouwing, citaat "
        "FROM signalen WHERE classificatie='kans' AND COALESCE(herbeoordeeld,0)=0"
    ).fetchall()
    print(f"Te herbeoordelen kansen: {len(rijen)}")

    telling = {"kans": 0, "contextafhankelijk": 0, "risico": 0, "verwijderen": 0, "overgeslagen": 0}
    for n, (sid, titel, ind, samv, onderb, cit) in enumerate(rijen, 1):
        oordeel = _herbeoordeel(titel, ind, samv or "", onderb or "", cit or "")
        if oordeel is None:
            telling["overgeslagen"] += 1
            # niet als herbeoordeeld markeren -> volgende keer opnieuw proberen
        elif oordeel == "verwijderen":
            conn.execute("DELETE FROM signalen WHERE id=?", (sid,))
            telling["verwijderen"] += 1
        else:
            conn.execute(
                "UPDATE signalen SET classificatie=?, herbeoordeeld=1 WHERE id=?",
                (oordeel, sid))
            telling[oordeel] += 1
        if n % 25 == 0:
            conn.commit()
            print(f"  {n}/{len(rijen)} | {telling}", flush=True)
    conn.commit()
    print(f"\nKlaar. Resultaat: {telling}")
    rest = conn.execute(
        "SELECT count(*) FROM signalen WHERE classificatie='kans' AND COALESCE(herbeoordeeld,0)=0"
    ).fetchone()[0]
    print(f"Nog te doen (volgende pass): {rest}")


if __name__ == "__main__":
    main()
