"""Laag 3 — Classificeren: toets een document aan de 10 beleidsindicatoren
via de Claude API en geef een gestructureerd oordeel terug.
"""
import os
import json
import re

from anthropic import Anthropic
from dotenv import load_dotenv

from config import INDICATOREN, MAX_TEKST_TEKENS, CLASSIFICATIE_MODEL
from verwerk import maak_fragment

load_dotenv()

GELDIGE_KLASSEN = {"kans", "risico", "contextafhankelijk"}

# Model komt uit config (CLASSIFICATIE_MODEL); standaard Haiku (goedkoop).
MODEL = CLASSIFICATIE_MODEL

_client = None


def _get_client() -> Anthropic:
    """Maak de client pas aan wanneer nodig, met een duidelijke foutmelding
    als de API-sleutel ontbreekt."""
    global _client
    if _client is None:
        sleutel = os.environ.get("ANTHROPIC_API_KEY", "")
        if not sleutel or sleutel.startswith("sk-ant-...") or sleutel == "sk-ant-...":
            raise RuntimeError(
                "Geen geldige ANTHROPIC_API_KEY gevonden. Zet je sleutel in het "
                ".env-bestand (verkrijgbaar via https://console.anthropic.com)."
            )
        _client = Anthropic(api_key=sleutel)
    return _client


SYSTEEM_PROMPT = f"""Je bent een neutrale, feitelijke beleidsanalist voor Today Development,
een ontwikkelaar van industrieel vastgoed. Je beoordeelt of een beleidsdocument een signaal
bevat dat relevant is voor industrieel vastgoed, op basis van deze 10 indicatoren:

{chr(10).join(f'{i["id"]}. {i["naam"]} (standaard: {i["classificatie"]})' for i in INDICATOREN)}

DEFINITIES:
- KANS: vergroot, versterkt of versnelt CONCREET de ontwikkelmogelijkheden voor
  industrieel/logistiek vastgoed. Alleen kans bij een aanwijsbare maatregel,
  ontwikkeling of besluit met een aannemelijk voordeel voor Today — niet bij een
  algemeen of positief klinkende vermelding.
- RISICO: beperkt, vertraagt of maakt onzeker.
- CONTEXTAFHANKELIJK: hangt af van type vastgoed (Layers-concept = milieucategorie 3.2) en locatie.

WANNEER IS IETS GÉÉN KANS — wees hier streng. Label dan contextafhankelijk, of laat
het signaal weg als het niet werkelijk relevant is:
- Algemene, positief klinkende beleidstaal zonder concrete maatregel (bv. "economie
  en werklocaties zijn belangrijk", "inzetten op een sterk vestigingsklimaat").
- Speculatieve ketens: als de "kans" alleen volgt uit "kan betekenen", "zou kunnen",
  "suggereert" of "biedt mogelijk ruimte" zonder dat het document een concrete
  maatregel benoemt → geen kans (hooguit contextafhankelijk).
- Transformatie of herontwikkeling die de industriële/werkfunctie juist WEGNEEMT
  (naar wonen of gemengd gebruik) — ook als het document zélf het woord "kansen"
  gebruikt. Verlies van industriegrond is voor Today een risico of niet relevant.
- Investeringen/voorzieningen (OV, infrastructuur) die primair op wonen of
  stationsgebieden zijn gericht en industrieterreinen alleen zijdelings raken.
- RELEVANTIE (1-5): hoe sterk en direct raakt dit signaal de ontwikkelmogelijkheden
  voor industrieel vastgoed? 5 = zeer sterk en concreet (bv. een vastgesteld besluit
  met directe, grote impact op een bedrijventerrein); 3 = duidelijk relevant maar
  indirect of beperkt van omvang; 1 = marginaal/zijdelings relevant.

PERSPECTIEF — beoordeel kans/risico ALTIJD vanuit Today (ontwikkelaar van
industrieel vastgoed), niet vanuit de partij in het document. Een maatregel die
negatief is voor de huidige gebruiker (bv. een veehouder of milieubelastend
bedrijf dat moet stoppen of verplaatsen) kan voor Today een KANS zijn — maar
ALLEEN als de vrijkomende grond voor industrie/logistiek beschikbaar of bestemd
komt. Gaat de vrijkomende ruimte naar WONINGBOUW, dan is dit signaal NIET RELEVANT
voor Today — neem het dan niet op. Is het onduidelijk wat er met de grond gebeurt:
contextafhankelijk en lagere relevantie.

BELANGRIJKE NUANCES:
- Netcongestie (indicator 4) valt grotendeels buiten gemeentelijk beleid (netbeheerders Liander/Stedin).
- Herstructurering met behoud werkbestemming = kans; transformatie naar wonen = risico.
- Vrijkomende grond door beëindiging/uitplaatsing van bestaande functies (ook
  agrarisch, bv. veehouderij, of milieubelastend) = KANS als die grond voor
  industrie/logistiek benut/bestemd wordt; gaat het naar woningbouw dan is het NIET
  RELEVANT (niet opnemen); is het onbekend = contextafhankelijk.

BELANGRIJK — één document kan MEERDERE indicatoren raken. Een visie op werklocaties
kan bijvoorbeeld tegelijk indicator 2 (beschikbaarheid), 8 (functieverruiming) en
9 (vestigingsbeleid) bevatten. Geef ELK relevant signaal apart terug. Voeg alleen
indicatoren toe die het document daadwerkelijk en concreet raakt — verzin niets.
Als het document niets relevants bevat, geef dan een lege lijst.

Voeg per signaal een "citaat" toe: een KORT, LETTERLIJK overgenomen fragment
(1-2 zinnen) uit de aangeleverde tekst waarop dit signaal is gebaseerd, zodat de
vindplaats in het document terug te zoeken is. Neem het exact over (niet
parafraseren). Laat leeg als er geen passende passage is.

Antwoord UITSLUITEND met JSON, geen extra tekst. Per relevant signaal één object:
{{"signalen": [
  {{"indicator_id": <1-10>, "classificatie": "kans"/"risico"/"contextafhankelijk", "relevantie": <1-5>, "samenvatting": "<1-2 zinnen>", "onderbouwing": "<waarom>", "citaat": "<kort letterlijk fragment uit de tekst>"}}
]}}"""


def _parse_json_antwoord(antwoord: str) -> dict:
    """Haal het JSON-object uit het modelantwoord, ook als er fences of
    extra tekst omheen staan."""
    schoon = antwoord.strip()
    schoon = schoon.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(schoon)
    except json.JSONDecodeError:
        # Terugval: pak het eerste {...}-blok uit de tekst.
        match = re.search(r"\{.*\}", schoon, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _schoon_signaal(s: dict) -> dict | None:
    """Valideer en normaliseer één signaal. Geeft None terug als het ongeldig is."""
    try:
        indicator_id = int(s.get("indicator_id"))
    except (TypeError, ValueError):
        return None
    if not 1 <= indicator_id <= 10:
        return None
    classificatie = s.get("classificatie")
    if classificatie not in GELDIGE_KLASSEN:
        classificatie = None
    try:
        relevantie = int(s.get("relevantie"))
        relevantie = relevantie if 1 <= relevantie <= 5 else None
    except (TypeError, ValueError):
        relevantie = None
    return {
        "indicator_id": indicator_id,
        "classificatie": classificatie,
        "relevantie": relevantie,
        "samenvatting": (s.get("samenvatting") or "").strip(),
        "onderbouwing": (s.get("onderbouwing") or "").strip(),
        "citaat": (s.get("citaat") or "").strip(),
    }


def classificeer(titel: str, tekst: str, zoekterm: str | None = None) -> list[dict]:
    """Classificeer één document tegen alle indicatoren.

    Geeft een LIJST van signalen terug (één per geraakte indicator). Lege lijst
    als het document niets relevants bevat of bij een fout (de pipeline slaat
    dan niets op).
    """
    # Slim fragment i.p.v. botte afkapping: begin + passages rond de zoekterm.
    fragment = maak_fragment(tekst, zoekterm, limiet=MAX_TEKST_TEKENS)
    try:
        bericht = _get_client().messages.create(
            model=MODEL,
            max_tokens=1500,
            # Prompt-caching: de vaste systeeminstructie wordt hergebruikt over veel
            # documenten heen, wat de invoerkosten flink drukt bij grote runs.
            system=[{"type": "text", "text": SYSTEEM_PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Titel: {titel}\n\nTekst:\n{fragment}"}],
        )
        antwoord = bericht.content[0].text.strip()
        resultaat = _parse_json_antwoord(antwoord)
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print(f"    classificatie-fout: {type(e).__name__}: {e}")
        return []

    rauwe = resultaat.get("signalen", []) if isinstance(resultaat, dict) else []
    signalen = []
    gezien = set()
    for s in rauwe:
        schoon = _schoon_signaal(s)
        if schoon and schoon["indicator_id"] not in gezien:
            gezien.add(schoon["indicator_id"])  # niet dezelfde indicator dubbel
            signalen.append(schoon)
    return signalen


def scoor_bestaand(titel: str, samenvatting: str, onderbouwing: str):
    """Geef alleen een relevantiescore (1-5) terug op basis van reeds bekende
    velden. Voor het bijwerken van bestaande signalen zonder de volledige
    tekst opnieuw te downloaden. Geeft None terug bij een fout."""
    prompt = (
        "Op basis van onderstaande analyse: geef een relevantiescore 1-5 voor "
        "industrieel vastgoed (5 = zeer sterk en concreet, 1 = marginaal).\n\n"
        f"Titel: {titel}\nSamenvatting: {samenvatting}\nOnderbouwing: {onderbouwing}\n\n"
        'Antwoord UITSLUITEND met JSON: {"relevantie": <1-5>}'
    )
    try:
        bericht = _get_client().messages.create(
            model=MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json_antwoord(bericht.content[0].text.strip())
        score = int(data.get("relevantie"))
        return score if 1 <= score <= 5 else None
    except Exception:
        return None


if __name__ == "__main__":
    # Test met één voorbeelddocument.
    voorbeeld_titel = "Aanwijzing bedrijventerrein Nieuw Overvecht"
    voorbeeld_tekst = (
        "De gemeente Utrecht wijst het bedrijventerrein Nieuw Overvecht aan als locatie "
        "waar bedrijven tot milieucategorie 3.2 zijn toegestaan. Het college wil de "
        "werkfunctie van dit bedrijventerrein behouden en versterken, en zet in op "
        "herstructurering met behoud van de bedrijfsbestemming. Transformatie naar wonen "
        "is op deze locatie niet aan de orde."
    )
    print("Classificatie van het voorbeelddocument:\n")
    signalen = classificeer(voorbeeld_titel, voorbeeld_tekst, zoekterm="bedrijventerrein")
    print(f"{len(signalen)} signaal/signalen:\n")
    print(json.dumps(signalen, indent=2, ensure_ascii=False))
