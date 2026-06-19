"""Bron: Omgevingsloket / DSO — geldende omgevingsplanregels per adres.

Geen documenten- of AI-bron: een live opvraging van het Digitaal Stelsel
Omgevingswet (DSO). Geeft per locatie de geldende regelingen (omgevingsdocumenten)
terug. Gebruikt de gratis DSO-sleutel (x-api-key); geen Anthropic-tokens.

Geverifieerd (zie verkenning):
- PRE-base: .../api/presenteren/v8/  — let op: PRE = testomgeving (testdata).
- POST /onderwerpen/_zoek met {"geometrie": {"type":"Point","coordinates":[RD_x, RD_y]}}
- Headers: x-api-key, Accept: application/hal+json, Content-Crs/Accept-Crs =
  http://www.opengis.net/def/crs/EPSG/0/28992 (RD).
- Adres -> RD-coördinaat via PDOK Locatieserver (gratis).
"""
import os
import re
import json

import requests
from dotenv import load_dotenv

load_dotenv()

PRE_BASE = ("https://service.pre.omgevingswet.overheid.nl/publiek/"
            "omgevingsdocumenten/api/presenteren/v8/")
PROD_BASE = ("https://service.omgevingswet.overheid.nl/publiek/"
             "omgevingsdocumenten/api/presenteren/v8/")
CRS_RD = "http://www.opengis.net/def/crs/EPSG/0/28992"
PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
UA = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1 (afstudeerproject)"}


def _key() -> str:
    # Nu de PRE-sleutel; voor productie later een prod-sleutel + PROD_BASE.
    return os.environ.get("DSO_PRE_API_KEY", "")


def _base() -> str:
    return PRE_BASE


def geocode_adres(adres: str) -> dict | None:
    """Zet een adres om naar RD-coördinaat + gemeente via PDOK. None bij geen hit."""
    try:
        r = requests.get(PDOK, params={
            "q": adres, "rows": 1,
            "fl": "weergavenaam,centroide_rd,gemeentenaam,type"},
            headers=UA, timeout=20)
        docs = r.json().get("response", {}).get("docs", [])
    except Exception:
        return None
    if not docs:
        return None
    d = docs[0]
    m = re.match(r"POINT\(([\d.]+) ([\d.]+)\)", d.get("centroide_rd", "") or "")
    if not m:
        return None
    return {
        "weergavenaam": d.get("weergavenaam"),
        "gemeente": d.get("gemeentenaam"),
        "type": d.get("type"),
        "rd_x": float(m.group(1)),
        "rd_y": float(m.group(2)),
    }


def _headers() -> dict:
    return {"x-api-key": _key(), "Accept": "application/hal+json",
            "Content-Type": "application/json",
            "Content-Crs": CRS_RD, "Accept-Crs": CRS_RD}


def _regeling_naam(href: str) -> str | None:
    try:
        r = requests.get(href, headers=_headers(), timeout=20)
        if r.status_code == 200:
            d = r.json()
            return d.get("officieleTitel") or d.get("opschrift") or d.get("naam")
    except Exception:
        pass
    return None


def regelingen_op_locatie(rd_x: float, rd_y: float, met_namen: bool = True) -> dict:
    """Geef de geldende regelingen (omgevingsdocumenten) op een RD-punt.
    Retourneert {"regelingen": [...]} of {"fout": "..."}."""
    if not _key():
        return {"fout": "Geen DSO_PRE_API_KEY ingesteld (zet 'm in .env / secrets)."}
    body = {"geometrie": {"type": "Point", "coordinates": [rd_x, rd_y]}}
    try:
        r = requests.post(_base() + "onderwerpen/_zoek", headers=_headers(),
                          data=json.dumps(body), timeout=30)
    except Exception as e:
        return {"fout": f"netwerkfout: {type(e).__name__}"}
    if r.status_code != 200:
        return {"fout": f"DSO gaf HTTP {r.status_code}"}
    regs = r.json().get("regelingen", [])
    uit = []
    for reg in regs:
        ident = reg.get("identificatie")
        href = (reg.get("_links", {}).get("regeling", {}) or {}).get("href")
        naam = _regeling_naam(href) if (met_namen and href) else None
        uit.append({"identificatie": ident, "naam": naam or ident, "href": href})
    return {"regelingen": uit}


def regels_op_adres(adres: str) -> dict:
    """Adres -> locatie + geldende regelingen. {"locatie":..., "regelingen":[...]}."""
    loc = geocode_adres(adres)
    if not loc:
        return {"fout": "Adres niet gevonden."}
    res = regelingen_op_locatie(loc["rd_x"], loc["rd_y"])
    res["locatie"] = loc
    return res


if __name__ == "__main__":
    import sys
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    print(f"Adres: {adres}")
    r = regels_op_adres(adres)
    loc = r.get("locatie")
    if loc:
        print(f"  -> {loc['weergavenaam']} | gemeente {loc['gemeente']} | RD {loc['rd_x']:.0f},{loc['rd_y']:.0f}")
    if r.get("fout"):
        print("  FOUT:", r["fout"])
    else:
        print(f"  {len(r['regelingen'])} geldende regeling(en):")
        for reg in r["regelingen"]:
            print("   -", (reg["naam"] or "")[:70])
