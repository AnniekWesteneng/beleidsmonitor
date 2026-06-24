"""Locatie-analyse: combineer de DSO-regels op een adres met een AI-duiding van
kansen en risico's voor industrieel vastgoed (Today).

Geen documentbron: een live uitvraag van het Omgevingsloket (DSO) op een punt,
gevolgd door een beknopte interpretatie door het Claude-model in termen van de
tien beleidsindicatoren.

Eerlijk over de grens: de duiding is gebaseerd op de DSO-METADATA (geldende
regelingen, hun activiteiten en thema's op de locatie), niet op de letterlijke
plantekst. Het omgevingsplan zelf blijft leidend.
"""
import json

from classificeer import _get_client, MODEL, INDICATOREN, _parse_json_antwoord
from bronnen.omgevingsloket import geocode_adres, onderwerpen_op_locatie

_IND = "\n".join(f'{i["id"]}. {i["naam"]}' for i in INDICATOREN)

PROMPT = f"""Je bent een beleidsanalist voor Today Development, ontwikkelaar van
industrieel/logistiek vastgoed. Je krijgt de geldende omgevingsregels op één
locatie uit het Digitaal Stelsel Omgevingswet (DSO): per bestuursniveau de
gereguleerde activiteiten en de thema's. Geef een beknopte, feitelijke duiding van
wat dit betekent voor industrieel vastgoed op deze plek.

Beoordeel in termen van deze indicatoren:
{_IND}

Wees concreet en streng: noem alleen kansen die een aanwijsbaar voordeel voor
industrie/logistiek opleveren, en risico's die de ontwikkeling echt beperken
(bv. milieuzonering, externe veiligheid, natuur/Natura 2000, water, geluid,
cultureel erfgoed). Baseer je op de aangeleverde activiteiten/thema's; verzin geen
regels die er niet staan. Als iets onduidelijk is, benoem het als aandachtspunt.

Geef bovenaan een HELDER EINDOORDEEL of deze locatie kansrijk is voor industrieel/
logistiek vastgoed, zodat dit in één oogopslag te zien is:
- "geschikt": locatie is industrieel/logistiek bestemd of goed benutbaar, weinig
  blokkades → interessant.
- "mits_voorwaarden": kansrijk maar met duidelijke beperkingen (bv. milieuzonering,
  externe veiligheid, geluid) die je eerst moet uitzoeken.
- "ongeschikt": overwegend wonen/natuur/beschermd of zware restricties → weinig
  kansrijk voor industrie.
Geef ook "kernpunt": één korte zin met de doorslaggevende reden.

Houd het beknopt: maximaal 5 punten per lijst, elk één korte zin.

Antwoord UITSLUITEND met JSON, geen tekst eromheen:
{{"geschiktheid": "geschikt"|"mits_voorwaarden"|"ongeschikt",
  "kernpunt": "<één korte zin: de doorslaggevende reden>",
  "samenvatting": "<2-3 zinnen>",
  "kansen": ["<kort, concreet>"],
  "risicos": ["<kort, concreet>"],
  "aandachtspunten": ["<kort>"]}}"""


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
    # Bouw een compacte, leesbare invoer voor het model: gemeente + provincie
    # activiteiten (de locatie-specifieke laag), plus alle thema's.
    blokken = []
    for r in regelingen:
        if r["niveau"] in ("gemeente", "provincie") and r["activiteiten"]:
            acts = r["activiteiten"][:60]
            blokken.append(f"{r['niveau_label']} — gereguleerde activiteiten:\n  "
                           + "\n  ".join(acts))
    rijk_ws = [r["niveau_label"] for r in regelingen
               if r["niveau"] in ("rijk", "waterschap")]
    inhoud = (
        f"Locatie: {loc.get('weergavenaam')} (gemeente {loc.get('gemeente')})\n\n"
        f"Thema's op deze locatie: {', '.join(themas) or '-'}\n\n"
        + "\n\n".join(blokken)
        + (f"\n\nDaarnaast gelden generieke rijks-/waterschapsregels: "
           f"{', '.join(sorted(set(rijk_ws)))}." if rijk_ws else "")
    )

    duiding = None
    try:
        b = _get_client().messages.create(
            model=MODEL, max_tokens=1400,
            system=[{"type": "text", "text": PROMPT,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": inhoud}],
        )
        duiding = _parse_json_antwoord(b.content[0].text.strip())
    except Exception as e:
        duiding = {"fout": f"AI-duiding mislukt: {type(e).__name__}"}

    return {"locatie": loc, "regelingen": regelingen, "themas": themas,
            "duiding": duiding}


if __name__ == "__main__":
    import sys
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    r = analyseer_adres(adres)
    print(json.dumps(r.get("duiding"), indent=2, ensure_ascii=False))
    print("\nThema's:", ", ".join(r.get("themas", [])))
