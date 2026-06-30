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


def _is_prod() -> bool:
    """Gebruik productie zodra er een prod-sleutel is; anders PRE (test)."""
    return bool(os.environ.get("DSO_PROD_API_KEY"))


def _key() -> str:
    # Prod-sleutel heeft voorrang; anders terugvallen op de PRE-sleutel.
    return os.environ.get("DSO_PROD_API_KEY") or os.environ.get("DSO_PRE_API_KEY", "")


def _base() -> str:
    return PROD_BASE if _is_prod() else PRE_BASE


def _pdok_zoek(q: str, fq: list[str]) -> dict | None:
    """Eén PDOK-bevraging; geeft de eerste doc terug of None."""
    params = {"q": q, "rows": 1,
              "fl": "weergavenaam,centroide_rd,gemeentenaam,type"}
    if fq:
        params["fq"] = fq
    try:
        r = requests.get(PDOK, params=params, headers=UA, timeout=20)
        docs = r.json().get("response", {}).get("docs", [])
    except Exception:
        return None
    return docs[0] if docs else None


def geocode_adres(adres: str) -> dict | None:
    """Zet een adres om naar RD-coördinaat + gemeente via PDOK. None bij geen hit.

    Verbeterd: filtert op echte adressen (type:adres) zodat het punt op het pand
    landt i.p.v. op de weg, en — als het adres een gemeente bevat (na de komma) —
    op die gemeente, zodat een niet-bestaand adres niet stilletjes in een andere
    gemeente belandt. Valt netjes terug als dat niets oplevert.
    """
    gem = adres.split(",")[-1].strip() if "," in adres else ""
    # Heuristiek: alleen als het laatste deel op een gemeentenaam lijkt (geen cijfers).
    gem = gem if gem and not any(c.isdigit() for c in gem) else ""

    pogingen = []
    if gem:
        pogingen.append((adres, ["type:adres", f'gemeentenaam:"{gem}"']))
    pogingen.append((adres, ["type:adres"]))
    pogingen.append((adres, []))  # laatste vangnet: vrije zoektocht

    d = None
    for q, fq in pogingen:
        d = _pdok_zoek(q, fq)
        if d:
            break
    if not d:
        return None
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


SUGGEST = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/suggest"


def suggest_adres(q: str, rows: int = 6) -> list[str]:
    """Adres-suggesties (PDOK) voor automatische aanvulling. Geeft een lijst
    weergavenamen terug; lege lijst bij geen treffer of fout."""
    if not q or len(q.strip()) < 3:
        return []
    try:
        r = requests.get(SUGGEST, params={"q": q, "rows": rows, "fq": "type:adres"},
                         headers=UA, timeout=10)
        docs = r.json().get("response", {}).get("docs", [])
        return [d.get("weergavenaam") for d in docs if d.get("weergavenaam")]
    except Exception:
        return []


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


import re as _re


def _strip_xml(inhoud: str) -> str:
    t = _re.sub(r"<[^>]+>", " ", inhoud or "")
    return _re.sub(r"\s+", " ", t).strip()


def perceelregels_op_locatie(rd_x: float, rd_y: float, max_regels: int = 25) -> dict:
    """De omgevingsplan-regels die SPECIFIEK op dit punt gelden (niet de
    gemeente-brede regels). Koppelt: punt -> activiteit-locaties -> juridische
    regels met een specifiek werkingsgebied -> regeltekst -> artikeltekst.

    Retourneert {"regels": [{"expressie":.., "tekst":..}], "gemeente_breed": n}
    of {"fout": ...}.
    """
    if not _key():
        return {"fout": "Geen DSO-sleutel ingesteld."}
    body = {"geometrie": {"type": "Point", "coordinates": [rd_x, rd_y]}}
    try:
        j = requests.post(_base() + "onderwerpen/_zoek", headers=_headers(),
                          data=json.dumps(body), timeout=30).json()
    except Exception as e:
        return {"fout": f"netwerkfout: {type(e).__name__}"}

    regels, gemeente_breed = [], 0
    # Per gemeentelijke regeling (omgevingsplan) de specifieke regels ophalen.
    for onderwerp in j.get("regelingen", []):
        if "/act/gm" not in onderwerp.get("identificatie", ""):
            continue
        punt_ala = set()
        for a in onderwerp.get("activiteiten", []):
            punt_ala.update(a.get("activiteitLocatieaanduidingen", []))
        links = onderwerp.get("_links", {})
        reg_href = (links.get("regeling", {}) or {}).get("href")
        ds_href = (links.get("documentstructuur", {}) or {}).get("href")
        if not reg_href:
            continue
        try:
            reg = requests.get(reg_href, headers=_headers(), timeout=30).json()
            ann_href = reg.get("_links", {}).get("annotaties", {}).get("href")
            ann = requests.get(ann_href, headers=_headers(), timeout=90).json()
            ds = requests.get(ds_href, headers=_headers(), timeout=90).json()
        except Exception as e:
            return {"fout": f"DSO-fout bij regels ophalen: {type(e).__name__}"}

        wid = {rt["identificatie"]: rt.get("wId") for rt in ann.get("regelteksten", [])}
        # Tekst per component-identificatie uit de documentstructuur.
        tekst_van = {}

        def _walk(n):
            if isinstance(n, dict):
                i, inh = n.get("identificatie"), n.get("inhoud")
                if i and inh:
                    tekst_van[i] = _strip_xml(inh)
                emb = n.get("_embedded", {})
                for v in (emb.get("documentComponenten", []) if isinstance(emb, dict) else []):
                    _walk(v)
            elif isinstance(n, list):
                for v in n:
                    _walk(v)
        _walk(ds)

        gezien = set()
        for jr in ann.get("regelsVoorIedereen", []):
            ids = {x["identificatie"] for x in jr.get("activiteitLocatieaanduidingen", [])}
            specifiek = any("ambtsgebied" not in lr for lr in jr.get("locatieRefs", []))
            if not (ids & punt_ala):
                continue
            if not specifiek:
                gemeente_breed += 1
                continue
            ref = jr.get("regeltekstRef")
            w = wid.get(ref)
            tekst = tekst_van.get(w)
            if tekst and w not in gezien:
                gezien.add(w)
                regels.append({"expressie": (w or "").split("__", 1)[-1], "tekst": tekst})

    return {"regels": regels[:max_regels], "gemeente_breed": gemeente_breed}


def voorbeschermingsregels_op_punt(rd_x: float, rd_y: float) -> list[dict]:
    """Geldende voorbereidingsbesluiten/voorbeschermingsregels op een RD-punt,
    uit het DSO (type 'Voorbeschermingsregels Omgevingsplan'). Vangt — anders dan
    Ruimtelijke Plannen — ook NIEUWE (na 2024) voorbereidingsbesluiten.
    """
    if not _key():
        return []
    body = {"geometrie": {"type": "Point", "coordinates": [rd_x, rd_y]}}
    try:
        j = requests.post(_base() + "onderwerpen/_zoek", headers=_headers(),
                          data=json.dumps(body), timeout=30).json()
    except Exception:
        return []
    # (identificatie, href) per regeling. Landelijke (Rijk, /act/mnre...) besluiten
    # slaan we over: die hebben een enorm werkingsgebied en zijn geen perceelsignaal.
    paren = [(r.get("identificatie", ""),
              (r.get("_links", {}).get("regeling", {}) or {}).get("href"))
             for r in j.get("regelingen", [])]
    paren = [(i, h) for i, h in paren if h and "/act/mnre" not in i]

    def _type_en_titel(par):
        try:
            d = requests.get(par[1], headers=_headers(), timeout=20).json()
            return d.get("type", {}), d.get("officieleTitel") or d.get("citeerTitel")
        except Exception:
            return {}, None

    uit = []
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as ex:
        for typ, titel in ex.map(_type_en_titel, paren):
            waarde = (typ or {}).get("waarde", "")
            if "Voorbescherming" in waarde or "Voorbereidingsbesluit" in waarde:
                uit.append({"naam": titel or waarde, "type": waarde})
    return uit


def _niveau(identificatie: str) -> tuple[str, str]:
    """Leid het bestuursniveau af uit de regeling-identificatie (de 'maker')."""
    try:
        maker = identificatie.split("/act/")[1].split("/")[0]
    except Exception:
        return ("overig", "Overig")
    if maker.startswith("gm"):
        return ("gemeente", "Gemeente (omgevingsplan)")
    if maker.startswith("pv"):
        return ("provincie", "Provincie")
    if maker.startswith("ws"):
        return ("waterschap", "Waterschap")
    if maker.startswith("mnre") or maker.startswith("rijk"):
        return ("rijk", "Rijk")
    return ("overig", "Overig")


def onderwerpen_op_locatie(rd_x: float, rd_y: float) -> dict:
    """Rijkere uitvraag op een RD-punt: per regeling het niveau, de activiteiten
    en de thema's. Retourneert een gestructureerd overzicht voor analyse/weergave.

    {"regelingen": [{niveau, niveau_label, identificatie, activiteiten:[namen],
                     themas:[waarden]}...], "themas": [unieke thema's]} of {"fout":...}.
    """
    if not _key():
        return {"fout": "Geen DSO-sleutel ingesteld (zet 'm in .env / secrets)."}
    body = {"geometrie": {"type": "Point", "coordinates": [rd_x, rd_y]}}
    try:
        r = requests.post(_base() + "onderwerpen/_zoek", headers=_headers(),
                          data=json.dumps(body), timeout=30)
    except Exception as e:
        return {"fout": f"netwerkfout: {type(e).__name__}"}
    if r.status_code != 200:
        return {"fout": f"DSO gaf HTTP {r.status_code}"}

    regs = r.json().get("regelingen", [])
    uit, alle_themas = [], set()
    for reg in regs:
        ident = reg.get("identificatie", "")
        niveau, label = _niveau(ident)
        acts = [a.get("naam") for a in reg.get("activiteiten", []) if a.get("naam")]
        themas = [t.get("waarde") for t in reg.get("themas", [])
                  if isinstance(t, dict) and t.get("waarde")]
        alle_themas.update(themas)
        uit.append({"niveau": niveau, "niveau_label": label,
                    "identificatie": ident, "activiteiten": acts, "themas": themas})
    # Sorteer: gemeente eerst, dan provincie, waterschap, rijk, overig.
    volgorde = {"gemeente": 0, "provincie": 1, "waterschap": 2, "rijk": 3, "overig": 4}
    uit.sort(key=lambda d: volgorde.get(d["niveau"], 9))
    return {"regelingen": uit, "themas": sorted(alle_themas)}


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
