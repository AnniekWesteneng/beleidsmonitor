"""Bron: Kadaster (open data via PDOK) — kadastraal perceel per adres.

Geen documenten- of AI-bron: een live opvraging van de Kadastrale Kaart van
PDOK (gratis open data; geen Anthropic-tokens, geen sleutel nodig).

Belangrijke afbakening: dit geeft het PERCEEL met de kadastrale aanduiding
(gemeente/sectie/nummer) en de oppervlakte. De werkelijke EIGENDOMSGEGEVENS
(wie is eigenaar — de Basisregistratie Kadaster/BRK) zijn een betaalde,
contractgebonden dienst en zitten hier bewust NIET in. Voedt indicator 6
(grondpositie) gedeeltelijk: perceel en omvang, niet de eigenaar.

Geverifieerd tegen de echte respons:
- WFS v5_0, typeNames=kadastralekaart:Perceel, GeoJSON-uitvoer.
- BBOX rond het RD-punt (EPSG:28992) levert het perceel op die locatie.
- Velden: kadastraleGemeenteWaarde, sectie, perceelnummer,
  kadastraleGrootteWaarde (m2), identificatieLokaalID.
- Adres -> RD-coordinaat via PDOK Locatieserver (zie omgevingsloket.geocode_adres).
"""
import sys
from pathlib import Path

import requests

# Maak imports werkend of het script nu vanuit de root of vanuit bronnen/ draait.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from bronnen.omgevingsloket import geocode_adres  # noqa: E402

BRON_NAAM = "Kadaster (Kadastrale Kaart, PDOK)"
WFS = "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0"
UA = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1 (afstudeerproject)"}


def perceel_op_locatie(rd_x: float, rd_y: float) -> dict:
    """Geef het kadastrale perceel op een RD-punt (EPSG:28992).
    Retourneert {"perceel": {...}} of {"fout": "..."}."""
    d = 1.5  # kleine bbox (meters) rond het punt
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": "kadastralekaart:Perceel", "count": 1,
        "srsName": "EPSG:28992", "outputFormat": "application/json",
        "bbox": f"{rd_x - d},{rd_y - d},{rd_x + d},{rd_y + d},EPSG:28992",
    }
    try:
        r = requests.get(WFS, params=params, headers=UA, timeout=30)
    except Exception as e:
        return {"fout": f"netwerkfout: {type(e).__name__}"}
    if r.status_code != 200:
        return {"fout": f"PDOK gaf HTTP {r.status_code}"}
    try:
        feats = r.json().get("features", [])
    except Exception:
        return {"fout": "onverwacht antwoord van PDOK"}
    if not feats:
        return {"fout": "Geen perceel gevonden op deze locatie."}
    p = feats[0].get("properties", {})
    gemeente = p.get("kadastraleGemeenteWaarde") or ""
    sectie = p.get("sectie") or ""
    nummer = p.get("perceelnummer")
    grootte = p.get("kadastraleGrootteWaarde")
    aanduiding = " ".join(str(x) for x in [gemeente, sectie, nummer] if x not in (None, ""))
    return {"perceel": {
        "aanduiding": aanduiding,
        "kadastrale_gemeente": gemeente,
        "sectie": sectie,
        "perceelnummer": nummer,
        "oppervlakte_m2": grootte,
        "oppervlakte_soort": p.get("soortGrootteWaarde"),
        "object_id": p.get("identificatieLokaalID"),
    }}


def perceel_op_adres(adres: str) -> dict:
    """Adres -> locatie + kadastraal perceel.
    {"locatie": {...}, "perceel": {...}} of {"fout": "..."}."""
    loc = geocode_adres(adres)
    if not loc:
        return {"fout": "Adres niet gevonden."}
    res = perceel_op_locatie(loc["rd_x"], loc["rd_y"])
    res["locatie"] = loc
    return res


if __name__ == "__main__":
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    print(f"Adres: {adres}")
    r = perceel_op_adres(adres)
    loc = r.get("locatie")
    if loc:
        print(f"  -> {loc['weergavenaam']} | gemeente {loc['gemeente']} | RD {loc['rd_x']:.0f},{loc['rd_y']:.0f}")
    if r.get("fout"):
        print("  FOUT:", r["fout"])
    else:
        p = r["perceel"]
        print(f"  Perceel: {p['aanduiding']}")
        print(f"  Oppervlakte: {p['oppervlakte_m2']:.0f} m2 ({p['oppervlakte_soort']})")
        print(f"  Kadastraal object: {p['object_id']}")
