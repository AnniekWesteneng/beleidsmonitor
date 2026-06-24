"""Bron: Ruimtelijke Plannen (DSO Opvragen API v4).

Geeft per locatie de CONCRETE planologische regels: de bestemming (functie),
maatvoering (bv. maximum bouwhoogte, bebouwingspercentage), functie- en
bouwaanduidingen, en geldende voorbereidingsbesluiten. Dit is harde brondata —
geen AI-interpretatie.

Auth: x-api-key (RUIMTELIJKE_PLANNEN_API_KEY). Coördinaten in RD (EPSG:28992).
"""
import os
import json

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://ruimte.omgevingswet.overheid.nl/ruimtelijke-plannen/api/opvragen/v4/"
# Plantypen met een toetsbare verbeelding (bestemming + maatvoering).
PLAN_MET_REGELS = {"bestemmingsplan", "omgevingsplan", "inpassingsplan",
                   "beheersverordening", "wijzigingsplan", "uitwerkingsplan"}


def _headers() -> dict:
    return {"x-api-key": os.environ.get("RUIMTELIJKE_PLANNEN_API_KEY", ""),
            "Content-Type": "application/json",
            "Content-Crs": "epsg:28992", "Accept-Crs": "epsg:28992"}


def _zoek(pad: str, rd_x: float, rd_y: float) -> list:
    body = {"_geo": {"contains": {"type": "Point", "coordinates": [rd_x, rd_y]}}}
    try:
        r = requests.post(BASE + pad, headers=_headers(),
                          data=json.dumps(body), timeout=30)
    except Exception:
        return []
    if r.status_code != 200:
        return []
    emb = r.json().get("_embedded", {})
    # _embedded heeft één sleutel met de lijst.
    for v in emb.values():
        if isinstance(v, list):
            return v
    return []


def details_op_punt(rd_x: float, rd_y: float) -> dict:
    """Concrete planregels op een RD-punt. Retourneert een dict met bestemming(en),
    maatvoeringen, functie-/bouwaanduidingen, voorbereidingsbesluiten en de plannen.
    """
    if not os.environ.get("RUIMTELIJKE_PLANNEN_API_KEY"):
        return {"fout": "Geen RUIMTELIJKE_PLANNEN_API_KEY ingesteld."}
    plannen = _zoek("plannen/_zoek", rd_x, rd_y)
    if not plannen:
        return {"plannen": [], "bestemmingen": [], "maatvoeringen": [],
                "functieaanduidingen": [], "bouwaanduidingen": [],
                "voorbereidingsbesluiten": []}

    # Voorbereidingsbesluiten, maar GEEN landelijke (Rijk, IMRO-code 0000) — die
    # hebben een enorm werkingsgebied (bv. hyperscale datacenters) en zijn geen
    # perceel-specifiek signaal; ze duiken anders bij half Nederland op als ruis.
    voorber = [{"naam": p.get("naam"), "id": p.get("id")}
               for p in plannen if p.get("type") == "voorbereidingsbesluit"
               and not str(p.get("id", "")).startswith("NL.IMRO.0000.")]
    plan_regels = [p for p in plannen if p.get("type") in PLAN_MET_REGELS]

    bestemmingen, maatvoeringen, functie_aand, bouw_aand = [], [], [], []
    gezien_maat = set()
    for p in plan_regels:
        pid, pnaam = p.get("id"), p.get("naam")
        for bv in _zoek(f"plannen/{pid}/bestemmingsvlakken/_zoek", rd_x, rd_y):
            bestemmingen.append({
                "naam": bv.get("naam"), "type": bv.get("type"),
                "hoofdgroep": bv.get("bestemmingshoofdgroep"),
                "artikel": bv.get("artikelnummer"), "plan": pnaam})
        for mv in _zoek(f"plannen/{pid}/maatvoeringen/_zoek", rd_x, rd_y):
            for o in (mv.get("omvang") or [{"naam": mv.get("naam"), "waarde": None}]):
                sleutel = (o.get("naam"), o.get("waarde"))
                if sleutel not in gezien_maat:
                    gezien_maat.add(sleutel)
                    maatvoeringen.append({"naam": o.get("naam"), "waarde": o.get("waarde")})
        for fa in _zoek(f"plannen/{pid}/functieaanduidingen/_zoek", rd_x, rd_y):
            if fa.get("naam"):
                functie_aand.append(fa["naam"])
        for ba in _zoek(f"plannen/{pid}/bouwaanduidingen/_zoek", rd_x, rd_y):
            if ba.get("naam"):
                bouw_aand.append(ba["naam"])

    return {
        "plannen": [{"naam": p.get("naam"), "type": p.get("type"), "id": p.get("id")}
                    for p in plannen],
        "bestemmingen": bestemmingen,
        "maatvoeringen": maatvoeringen,
        "functieaanduidingen": sorted(set(functie_aand)),
        "bouwaanduidingen": sorted(set(bouw_aand)),
        "voorbereidingsbesluiten": voorber,
    }


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bronnen.omgevingsloket import geocode_adres
    adres = " ".join(sys.argv[1:]) or "Atoomweg 50, Utrecht"
    loc = geocode_adres(adres)
    d = details_op_punt(loc["rd_x"], loc["rd_y"])
    print(json.dumps(d, ensure_ascii=False, indent=2))
