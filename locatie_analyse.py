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
                                    voorbeschermingsregels_op_punt)
from bronnen.ruimtelijke_plannen import details_op_punt

_IND = "\n".join(f'{i["id"]}. {i["naam"]}' for i in INDICATOREN)

PROMPT = f"""Je bent een beleidsanalist voor Today Development, ontwikkelaar van
industrieel/logistiek vastgoed. Je krijgt voor één locatie de CONCRETE planologische
gegevens uit de Ruimtelijke Plannen / het omgevingsplan: de bestemming, de
maatvoering (bv. maximum bouwhoogte, bebouwingspercentage), functie-/bouwaanduidingen
(bv. toegestane milieucategorie), eventuele voorbereidingsbesluiten, plus de thema's
die gelden. Duid wat dit betekent voor industrieel/logistiek vastgoed hier.

Beoordeel in termen van deze indicatoren:
{_IND}

Baseer je UITSLUITEND op de aangeleverde gegevens; verzin geen waarden die er niet
staan. Verwijs concreet naar de bestemming, de maxima en de toegestane categorie.

Over voorbereidingsbesluiten: een voorbereidingsbesluit betekent dat er een
planologische WIJZIGING in voorbereiding is. Verzin NIET de strekking of richting
ervan op basis van alleen de naam (een besluit kan iets juist beperken óf mogelijk
maken). Behandel het als aandachtspunt "uitzoeken bij de bron", en laat een
voorbereidingsbesluit waarvan de strekking onbekend is het eindoordeel NIET
automatisch op "ongeschikt" zetten — weeg het mee als onzekerheid, niet als
blokkade. Een besluit dat specifiek over een ánder gebruik gaat (bv. hyperscale
datacenters of detailhandel) zegt op zichzelf weinig over industrie/logistiek.

Geef een HELDER EINDOORDEEL of deze locatie kansrijk is voor industrieel/logistiek
vastgoed (één oogopslag):
- "geschikt": industrieel/logistiek benutbaar, weinig blokkades → interessant.
- "mits_voorwaarden": kansrijk maar met duidelijke beperkingen (milieuzonering,
  externe veiligheid, geluid, erfgoed, archeologie) die je eerst moet uitzoeken.
- "ongeschikt": uit de gegevens blijkt een echte beperking (bv. bestemming wonen/
  natuur/beschermd, of een regel die industrie uitsluit) → weinig kansrijk.
- "onbekend": er is GEEN bestemming en GEEN maatvoering aangeleverd → te weinig
  gegevens om te oordelen. Gebruik dit i.p.v. "ongeschikt"; concludeer NOOIT
  "ongeschikt" louter omdat gegevens ontbreken.
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

    # Concrete planregels (bestemming, bouwhoogte, categorie, VB) — harde brondata.
    rp = details_op_punt(loc["rd_x"], loc["rd_y"])
    # Thema's uit het DSO voor extra context (lichte uitvraag; mag ontbreken).
    dso = onderwerpen_op_locatie(loc["rd_x"], loc["rd_y"])
    themas = dso.get("themas", []) if not dso.get("fout") else []

    best = rp.get("bestemmingen", [])
    maat = rp.get("maatvoeringen", [])
    func = rp.get("functieaanduidingen", [])
    # Voorbereidingsbesluiten: DSO (actueel, ook ná 2024) + Ruimtelijke Plannen,
    # ontdubbeld op naam. DSO is leidend en future-proof.
    import re as _re

    def _vb_kern(naam):
        # Normaliseer: haal type-woorden weg, hou de kern (bv. 'hyperscaledatacent').
        s = naam.lower()
        for w in ("voorbeschermingsregels", "voorbereidingsbesluit",
                  "voorbescherming", "omgevingsplan"):
            s = s.replace(w, "")
        return _re.sub(r"[^a-z]", "", s)[:12]

    vb_kernen, vb = set(), []
    for bron in (voorbeschermingsregels_op_punt(loc["rd_x"], loc["rd_y"]),
                 rp.get("voorbereidingsbesluiten", [])):
        for v in bron:
            naam = (v.get("naam") or "").strip()
            kern = _vb_kern(naam)
            if naam and kern not in vb_kernen:
                vb_kernen.add(kern)
                vb.append({"naam": naam})
    best_txt = ", ".join(b["naam"] for b in best if b.get("naam")) or "-"
    maat_txt = "; ".join(f"{m.get('naam')}={m.get('waarde')}" for m in maat) or "-"
    func_txt = ", ".join(func) or "-"
    vb_txt = ", ".join(v["naam"] for v in vb) or "geen"
    inhoud = (
        f"Locatie: {loc.get('weergavenaam')} (gemeente {loc.get('gemeente')})\n"
        f"Bestemming(en): {best_txt}\n"
        f"Maatvoering: {maat_txt}\n"
        f"Functie-/bouwaanduidingen: {func_txt}\n"
        f"Voorbereidingsbesluiten: {vb_txt}\n"
        f"Thema's (DSO): {', '.join(themas) or '-'}"
    )

    duiding = {"fout": "AI-duiding mislukt"}
    for poging in range(3):  # enkele hapering of formatfout opvangen
        try:
            b = _get_client().messages.create(
                model=MODEL, max_tokens=1400,
                system=[{"type": "text", "text": PROMPT,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": inhoud}],
            )
            duiding = _parse_json_antwoord(b.content[0].text.strip())
            if isinstance(duiding, dict) and duiding.get("geschiktheid"):
                break  # geslaagd
        except Exception as e:
            duiding = {"fout": f"AI-duiding mislukt: {type(e).__name__}"}

    return {"locatie": loc, "planregels": rp, "themas": themas,
            "voorbereidingsbesluiten": vb, "duiding": duiding}


if __name__ == "__main__":
    import sys
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    r = analyseer_adres(adres)
    print(json.dumps(r.get("duiding"), indent=2, ensure_ascii=False))
    print("\nThema's:", ", ".join(r.get("themas", [])))
