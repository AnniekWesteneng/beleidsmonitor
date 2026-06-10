"""Laag 1 — Bron: Officiële Bekendmakingen (KOOP) via de SRU-API.

Best gestructureerde bron: open, gratis, dagelijks geactualiseerd, XML.
Endpoint: https://repository.overheid.nl/sru  (querytaal: CQL)

Geverifieerd tegen de echte API (zie de _verken_sru*.py-scripts):
- Filteren op gemeente gaat via het CQL-veld  dt.creator="<naam>".
- Vrije-tekst gaat via  cql.textAndIndexes="<term>".
- Sommige gemeenten delen hun naam met de PROVINCIE (bv. Utrecht). Die
  provinciale stukken verschijnen als publicatienaam 'Provinciaal blad' en
  filteren we eruit.
- 'Den Haag' staat onder twee creator-namen: 'Den Haag' én ''s-Gravenhage'.
- De dienst throttelt bij te snelle bevraging -> retry-met-backoff.
"""
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Maak imports werkend of het script nu vanuit de root of vanuit bronnen/ draait.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from verwerk import haal_documenttekst  # noqa: E402
from config import VANAF_JAAR, INCLUSIEF_PROVINCIE  # noqa: E402

SRU_ENDPOINT = "https://repository.overheid.nl/sru"
BRON_NAAM = "Officiële Bekendmakingen"
HEADERS = {
    "User-Agent": "Beleidsmonitor-TodayDevelopment/0.1 (afstudeerproject; contact via Today Development)"
}

# Publicaties die NIET van de gemeente zijn maar wel dezelfde creator-naam delen.
NIET_GEMEENTELIJK = {"Provinciaal blad", "Waterschapsblad"}

# Gemeenten die in de data onder meerdere namen voorkomen.
GEMEENTE_ALIASSEN = {
    "Den Haag": ["Den Haag", "'s-Gravenhage"],
}


def _creator_clause(gemeente: str) -> str:
    namen = GEMEENTE_ALIASSEN.get(gemeente, [gemeente])
    return " or ".join(f'dt.creator="{naam}"' for naam in namen)


def _sru_get(query: str, max_records: int, pogingen: int = 4) -> str | None:
    """SRU-aanroep met retry-met-backoff bij tijdelijke onbeschikbaarheid."""
    params = {
        "operation": "searchRetrieve",
        "version": "2.0",
        "maximumRecords": str(max_records),
        "query": query,
    }
    for poging in range(1, pogingen + 1):
        try:
            resp = requests.get(SRU_ENDPOINT, params=params, headers=HEADERS, timeout=60)
        except Exception as e:
            wacht = 5 * poging
            print(f"    netwerkfout ({type(e).__name__}), wacht {wacht}s...")
            time.sleep(wacht)
            continue
        if "Dienst tijdelijk niet beschikbaar" in resp.text or resp.status_code >= 500:
            wacht = 8 * poging
            print(f"    dienst even niet beschikbaar, wacht {wacht}s...")
            time.sleep(wacht)
            continue
        return resp.text
    print("    SRU bleef onbeschikbaar na alle pogingen.")
    return None


def _eerste_tekst(rec, *namen):
    """Geef de tekst van het eerste gevonden veld terug (of '')."""
    for naam in namen:
        el = rec.find(naam)
        if el and el.text.strip():
            return el.text.strip()
    return ""


def haal_bekendmakingen(gemeente: str, zoekterm: str, max_resultaten: int = 20,
                        met_tekst: bool = True) -> list[dict]:
    """Haal bekendmakingen op voor een gemeente + zoekterm.

    Geeft per document een dict terug met:
      gemeente, titel, documenttype, bron, datum, url, tekst
    """
    # Filter op vanaf-jaar en sorteer nieuwste eerst, zodat oude stukken
    # (bv. 2010) wegvallen en de actueelste documenten bovenaan komen.
    query = (
        f'({_creator_clause(gemeente)}) '
        f'and (cql.textAndIndexes="{zoekterm}") '
        f'and (dt.date>="{VANAF_JAAR}-01-01") '
        f'sortBy dt.date/sort.descending'
    )
    xml = _sru_get(query, max_resultaten)
    if xml is None:
        return []

    soup = BeautifulSoup(xml, "lxml-xml")
    resultaten = []
    for rec in soup.find_all("record"):
        publicatienaam = _eerste_tekst(rec, "publicatienaam")
        # Provincie/waterschap delen soms de naam met de gemeente. Standaard nemen
        # we ze mee (INCLUSIEF_PROVINCIE); zet die vlag op False om ze te negeren.
        if not INCLUSIEF_PROVINCIE and publicatienaam in NIET_GEMEENTELIJK:
            continue

        # URLs uit enrichedData
        preferred_url = _eerste_tekst(rec, "preferredUrl")
        xml_url = html_url = pdf_url = None
        for it in rec.find_all("itemUrl"):
            m = it.get("manifestation")
            if m == "xml":
                xml_url = it.text.strip()
            elif m == "html":
                html_url = it.text.strip()
            elif m == "pdf":
                pdf_url = it.text.strip()

        tekst = ""
        if met_tekst:
            tekst = haal_documenttekst(xml_url, html_url, pdf_url)
            time.sleep(1)  # beleefde pauze tussen documentdownloads

        resultaten.append({
            "gemeente": gemeente,
            "titel": _eerste_tekst(rec, "title") or "(zonder titel)",
            "documenttype": publicatienaam or _eerste_tekst(rec, "type"),
            "bron": BRON_NAAM,
            "datum": _eerste_tekst(rec, "date", "available", "modified"),
            "url": preferred_url,
            "tekst": tekst,
            # URLs bewaren zodat de pipeline de tekst later kan ophalen
            # (alleen voor nog niet verwerkte documenten -> kostenbesparend).
            "xml_url": xml_url,
            "html_url": html_url,
            "pdf_url": pdf_url,
        })

    return resultaten


# --- Eenvormige interface met andere bronnen (gebruikt door de pipeline) ---

def haal(gemeente: str, zoekterm: str, max_resultaten: int = 20) -> list[dict]:
    """Metadata ophalen (zonder tekst) zodat de pipeline al-verwerkte
    documenten goedkoop kan overslaan vóór de tekst-download."""
    return haal_bekendmakingen(gemeente, zoekterm,
                               max_resultaten=max_resultaten, met_tekst=False)


def vul_tekst(doc: dict) -> str:
    """Tekst nu pas ophalen via de bewaarde document-URLs (XML -> HTML -> PDF)."""
    return haal_documenttekst(doc.get("xml_url"), doc.get("html_url"), doc.get("pdf_url"))


if __name__ == "__main__":
    # Testaanroep zoals het bouwplan vraagt: Utrecht + bedrijventerrein, eerste 3.
    print("Test: Utrecht / bedrijventerrein (eerste 3 resultaten)\n")
    docs = haal_bekendmakingen("Utrecht", "bedrijventerrein", max_resultaten=3)
    print(f"\nAantal teruggegeven documenten: {len(docs)}\n")
    for i, d in enumerate(docs, 1):
        print(f"--- Document {i} ---")
        print(f"  Titel       : {d['titel']}")
        print(f"  Type        : {d['documenttype']}")
        print(f"  Datum       : {d['datum']}")
        print(f"  Gemeente    : {d['gemeente']}")
        print(f"  URL         : {d['url']}")
        print(f"  Tekstlengte : {len(d['tekst'])} tekens")
        print(f"  Tekstbegin  : {d['tekst'][:200]!r}\n")
