"""Locatie-analyse: combineer de DSO-regels op een adres met een AI-duiding van
kansen en risico's voor industrieel vastgoed (Today).

Geen documentbron: een live uitvraag van het Omgevingsloket (DSO) op een punt.
Naast de thema's worden de PERCEEL-SPECIFIEKE omgevingsplanregels (echte
artikeltekst) opgehaald en door het Claude-model geduid: wat geldt hier concreet,
en is er bv. een voorbereidingsbesluit of een bouw-/gebruiksbeperking.

Eerlijk over de grens: de regels komen letterlijk uit het DSO; de duiding is een
AI-interpretatie. Het omgevingsplan zelf blijft leidend.
"""
import json

from classificeer import _get_client, MODEL, INDICATOREN, _parse_json_antwoord
from bronnen.omgevingsloket import (geocode_adres, onderwerpen_op_locatie,
                                    perceelregels_op_locatie)

_IND = "\n".join(f'{i["id"]}. {i["naam"]}' for i in INDICATOREN)

PROMPT = f"""Je bent een beleidsanalist voor Today Development, ontwikkelaar van
industrieel/logistiek vastgoed. Je krijgt voor één locatie: (a) de thema's die er
gelden en (b) de PERCEEL-SPECIFIEKE omgevingsplanregels — de letterlijke
artikeltekst die juist op dit perceel van toepassing is. Duid wat dit concreet
betekent voor industrieel vastgoed hier.

Beoordeel in termen van deze indicatoren:
{_IND}

Baseer je op de aangeleverde regelteksten en thema's; verzin geen regels die er niet
staan. Citeer concrete beperkingen die in de regels staan (bv. vergunningplicht,
maximale maten, oppervlakte-/dieptegrenzen, toegestane functies, max. aantal
bedrijven, een voorbereidingsbesluit). Staat een exacte waarde niet in de
aangeleverde tekst, verzin die dan niet.

Geef een HELDER EINDOORDEEL of deze locatie kansrijk is voor industrieel/logistiek
vastgoed (één oogopslag):
- "geschikt": industrieel/logistiek benutbaar, weinig blokkades → interessant.
- "mits_voorwaarden": kansrijk maar met duidelijke beperkingen (milieuzonering,
  externe veiligheid, geluid, erfgoed, archeologie) die je eerst moet uitzoeken.
- "ongeschikt": overwegend wonen/natuur/beschermd of zware restricties → weinig
  kansrijk.
Geef ook "kernpunt": één korte zin met de doorslaggevende reden.

Zet "voorbereidingsbesluit" op een korte omschrijving ALS uit de regels blijkt dat
er een voorbereidingsbesluit of voorbereidingsbescherming geldt; anders lege string.

Vul "let_op" met de 3-6 dingen die je VOORAF moet weten voor dit perceel, kort en
concreet, ONTLEEND AAN de regelteksten: bouwen/bouwbeperkingen, toegestaan gebruik/
functie- en aantalsbeperkingen, en bijzondere zones (geluid, externe veiligheid,
archeologie, natuur, water). Noem concrete waarden als ze in de tekst staan.

Antwoord UITSLUITEND met JSON, geen tekst eromheen:
{{"geschiktheid": "geschikt"|"mits_voorwaarden"|"ongeschikt",
  "kernpunt": "<één korte zin: de doorslaggevende reden>",
  "voorbereidingsbesluit": "<korte omschrijving of lege string>",
  "let_op": ["<kort, concreet, ontleend aan de regels>"],
  "kansen": ["<kort, concreet>"],
  "risicos": ["<kort, concreet>"]}}"""


def analyseer_adres(adres: str) -> dict:
    """Adres -> locatie + DSO-regels (per niveau + thema's) + AI-duiding.

    Retourneert {"locatie":..., "regelingen":[...], "themas":[...],
    "duiding":{...}} of {"fout":...}.
    """
    loc = geocode_adres(adres)
    if not loc:
        return {"fout": "Adres niet gevonden."}
    dso = onderwerpen_op_locatie(loc["rd_x"], loc["rd_y"])
    if dso.get("fout"):
        return {"locatie": loc, "fout": dso["fout"]}

    regelingen, themas = dso["regelingen"], dso["themas"]
    # Perceel-specifieke omgevingsplanregels (echte artikeltekst) ophalen.
    pr = perceelregels_op_locatie(loc["rd_x"], loc["rd_y"])
    perceelregels = pr.get("regels", [])

    regelblok = "\n\n".join(
        f"Regel ({r['expressie']}): {r['tekst']}" for r in perceelregels
    ) or "(geen perceel-specifieke omgevingsplanregels gevonden op dit punt)"
    inhoud = (
        f"Locatie: {loc.get('weergavenaam')} (gemeente {loc.get('gemeente')})\n\n"
        f"Thema's op deze locatie: {', '.join(themas) or '-'}\n\n"
        f"Perceel-specifieke omgevingsplanregels (letterlijke tekst):\n\n{regelblok}"
    )

    duiding = {"fout": "AI-duiding mislukt"}
    for poging in range(3):  # enkele hapering of formatfout opvangen
        try:
            b = _get_client().messages.create(
                model=MODEL, max_tokens=1600,
                system=[{"type": "text", "text": PROMPT,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": inhoud}],
            )
            duiding = _parse_json_antwoord(b.content[0].text.strip())
            if isinstance(duiding, dict) and duiding.get("geschiktheid"):
                break  # geslaagd
        except Exception as e:
            duiding = {"fout": f"AI-duiding mislukt: {type(e).__name__}"}

    return {"locatie": loc, "regelingen": regelingen, "themas": themas,
            "perceelregels": perceelregels, "duiding": duiding}


if __name__ == "__main__":
    import sys
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    r = analyseer_adres(adres)
    print(json.dumps(r.get("duiding"), indent=2, ensure_ascii=False))
    print("\nThema's:", ", ".join(r.get("themas", [])))
