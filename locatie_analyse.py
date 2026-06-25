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
- "onbekend": er is GEEN hoofdbestemming (enkelbestemming) én GEEN maatvoering
  aangeleverd → te weinig gegevens om te oordelen. Gebruik dit i.p.v. "ongeschikt";
  concludeer NOOIT "ongeschikt" louter omdat gegevens ontbreken. Let op:
  dubbelbestemmingen (Waarde-archeologie, grondwater, "Openbare ruimte",
  "Kostenverhaalsgebied" e.d.) zijn GEEN hoofdbestemming — baseer het eindoordeel
  daar niet op; als alleen die er zijn, is het "onbekend".
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
    enkel = [b for b in best if b.get("type") == "enkelbestemming"]
    dubbel = [b for b in best if b.get("type") != "enkelbestemming"]
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
    enkel_txt = ", ".join(b["naam"] for b in enkel if b.get("naam")) or "-"
    dubbel_txt = ", ".join(b["naam"] for b in dubbel if b.get("naam")) or "-"
    maat_txt = "; ".join(f"{m.get('naam')}={m.get('waarde')}" for m in maat) or "-"
    func_txt = ", ".join(func) or "-"
    vb_txt = ", ".join(v["naam"] for v in vb) or "geen"
    inhoud = (
        f"Locatie: {loc.get('weergavenaam')} (gemeente {loc.get('gemeente')})\n"
        f"Hoofdbestemming (enkelbestemming): {enkel_txt}\n"
        f"Dubbelbestemmingen (Waarde-/beschermings-lagen, GEEN hoofdbestemming): {dubbel_txt}\n"
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


_VB_RELEVANT = (
    "bedrijventerrein", "bedrijvenpark", "bedrijfsterrein", "werklocatie",
    "werkgebied", "industrie", "industrieel", "logistiek", "datacenter",
    "datacentra", "milieucategorie", "milieuzonering", "transformatie",
    "herontwikkeling", "herstructurering", "haven", "bedrijfsunit",
    "verzamelgebouw", "kantoor", "bedrijf",
)


def vb_relevant(naam: str) -> bool:
    """Grove inschatting of een voorbereidingsbesluit relevant is voor industrieel/
    logistiek vastgoed, op basis van trefwoorden in de naam. Onderwerp-specifieke
    besluiten (tabakszaken, hotels, darkstores, geitenhouderijen, ...) vallen af."""
    n = (naam or "").lower()
    return any(k in n for k in _VB_RELEVANT)


def quick_check(adres: str) -> dict:
    """Lichte check voor de volglijst — GEEN AI/Anthropic (werkt dus ook bij
    bereikte API-limiet): bestemming, maatvoering en voorbereidingsbesluit(en)."""
    import re as _re
    loc = geocode_adres(adres)
    if not loc:
        return {"adres": adres, "fout": "Adres niet gevonden."}
    rp = details_op_punt(loc["rd_x"], loc["rd_y"])

    def _kern(naam):
        s = naam.lower()
        for w in ("voorbeschermingsregels", "voorbereidingsbesluit",
                  "voorbescherming", "omgevingsplan"):
            s = s.replace(w, "")
        return _re.sub(r"[^a-z]", "", s)[:12]

    vbs, kernen = [], set()
    for bron in (voorbeschermingsregels_op_punt(loc["rd_x"], loc["rd_y"]),
                 rp.get("voorbereidingsbesluiten", [])):
        for v in bron:
            naam = (v.get("naam") or "").strip()
            if naam and _kern(naam) not in kernen:
                kernen.add(_kern(naam))
                vbs.append({"naam": naam})
    enkel = [b for b in rp.get("bestemmingen", []) if b.get("type") == "enkelbestemming"]
    return {
        "adres": adres, "locatie": loc, "voorbereidingsbesluiten": vbs,
        "bestemming": ", ".join(dict.fromkeys(
            b["naam"] for b in enkel if b.get("naam"))) or "-",
        "maatvoeringen": rp.get("maatvoeringen", []),
    }


def _latin1(s: str) -> str:
    """Maak tekst geschikt voor de standaard-PDF-fonts (latin-1)."""
    repl = {"€": "EUR", "→": "->", "≥": ">=", "–": "-", "—": "-", "•": "-",
            "★": "*", "☆": "*", "’": "'", "‘": "'", "“": '"', "”": '"', "²": "2"}
    for a, b in repl.items():
        s = (s or "").replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def pdf_rapport(res: dict) -> bytes:
    """Maak een PDF-rapport van een adresanalyse (resultaat van analyseer_adres)."""
    from datetime import date
    from fpdf import FPDF

    loc = res.get("locatie", {}) or {}
    rp = res.get("planregels", {}) or {}
    d = res.get("duiding", {}) or {}
    enkel = [b for b in rp.get("bestemmingen", []) if b.get("type") == "enkelbestemming"]

    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    def line(t, size=10, style="", h=5, color=(0, 0, 0)):
        pdf.set_font("Helvetica", style, size)
        pdf.set_text_color(*color)
        pdf.multi_cell(0, h, _latin1(t), new_x="LMARGIN", new_y="NEXT")

    line("Locatieanalyse industrieel vastgoed", 16, "B", 9)
    line(f"{loc.get('weergavenaam', '')}  -  gemeente {loc.get('gemeente') or '-'}", 11)
    line("Beleidsmonitor Today Development - gegenereerd op " + date.today().isoformat(),
         8, "I", 5, (120, 120, 120))
    pdf.ln(2)

    label = {"geschikt": "Interessant voor industrieel vastgoed",
             "mits_voorwaarden": "Mogelijk interessant, mits voorwaarden",
             "ongeschikt": "Weinig kansrijk voor industrieel vastgoed",
             "onbekend": "Onvoldoende planologische gegevens"}.get(d.get("geschiktheid"))
    if label:
        line("Eindoordeel: " + label, 12, "B", 7)
        if d.get("kernpunt"):
            line(d["kernpunt"])
        pdf.ln(1)

    vbs = res.get("voorbereidingsbesluiten", [])
    if vbs:
        line("Voorbereidingsbesluit(en) van kracht", 11, "B", 6)
        for v in vbs:
            line("- " + (v.get("naam") or ""))
        pdf.ln(1)

    line("Planologische feiten", 11, "B", 6)
    if enkel:
        line("Bestemming: " + ", ".join(
            dict.fromkeys(b["naam"] for b in enkel if b.get("naam"))))
    for m in rp.get("maatvoeringen", []):
        line(f"{m.get('naam')}: {m.get('waarde')}")
    if rp.get("functieaanduidingen"):
        line("Toegestane functie/categorie: " + ", ".join(rp["functieaanduidingen"]))
    if not (enkel or rp.get("maatvoeringen")):
        line("Geen digitale bestemming gevonden op dit punt.")
    pdf.ln(1)

    if d.get("kansen"):
        line("Kansen", 11, "B", 6)
        for k in d["kansen"]:
            line("- " + k)
    if d.get("risicos"):
        line("Risico's", 11, "B", 6)
        for r in d["risicos"]:
            line("- " + r)
    pdf.ln(2)

    line("Bron: Ruimtelijke Plannen / Omgevingsloket (DSO). De kans/risico-duiding is een "
         "AI-interpretatie; het omgevingsplan blijft leidend. Controleer via 'Regels op de kaart'.",
         8, "I", 4, (120, 120, 120))
    return bytes(pdf.output())


if __name__ == "__main__":
    import sys
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    r = analyseer_adres(adres)
    print(json.dumps(r.get("duiding"), indent=2, ensure_ascii=False))
    print("\nThema's:", ", ".join(r.get("themas", [])))
