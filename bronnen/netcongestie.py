"""Bron: netcongestie-capaciteitskaart (Netbeheer Nederland).

Geen documentenbron maar een LIVE statusbron: per voedingsgebied (netvlak rond
een onderstation) de transportcapaciteit voor afname en opwek. Open ArcGIS-
FeatureServer, geen sleutel/tokens nodig.

Geverifieerd (zie _verken_netcongestie.py): granulariteit = voedingsgebied,
koppelbaar aan een gemeente via de naam. Status zit in 'afname'/'opwek' (0-3).
"""
import requests

SERVICE = ("https://services.arcgis.com/nSZVuSZjHpEZZbRo/arcgis/rest/services/"
           "Capaciteitskaart_elektriciteitsnet_v2_afname/FeatureServer/0/query")
KAART_URL = "https://capaciteitskaart.netbeheernederland.nl/"
HEADERS = {"User-Agent": "Beleidsmonitor-TodayDevelopment/0.1 (afstudeerproject)"}

# Statuscode -> (emoji, label). Afgeleid uit de legenda van de kaart.
STATUS = {
    0: ("🟢", "ruim beschikbaar"),
    1: ("🟡", "beperkt beschikbaar"),
    2: ("🟠", "in onderzoek (wachtrij)"),
    3: ("🔴", "tekort (wachtrij)"),
}

# Zoeknaam per gemeente (de voedingsgebieden heten naar plaats/wijk).
NAAM_ALIASSEN = {
    "Den Haag": "Den Haag",
}


def label(code) -> str:
    emoji, tekst = STATUS.get(code, ("⚪", "onbekend"))
    return f"{emoji} {tekst}"


def _zoekterm(gemeente: str) -> str:
    return NAAM_ALIASSEN.get(gemeente, gemeente)


def haal_netcongestie(gemeenten) -> dict:
    """Geef per gemeente een lijst voedingsgebieden met netstatus terug."""
    resultaat = {}
    for gemeente in gemeenten:
        term = _zoekterm(gemeente).replace("'", "''")  # SQL-escape
        params = {
            "where": f"voedingsgebied_naam LIKE '%{term}%'",
            "outFields": ("voedingsgebied_naam,afname,opwek,wachtrij_afname,"
                          "wachtrij_invoeding,RNB"),
            "f": "json", "returnGeometry": "false",
        }
        try:
            r = requests.get(SERVICE, params=params, headers=HEADERS, timeout=30)
            features = r.json().get("features", [])
        except Exception:
            features = []

        # Dedupliceer per voedingsgebied; neem de zwaarste status (hoogste code).
        per_gebied = {}
        for f in features:
            a = f.get("attributes", {})
            naam = (a.get("voedingsgebied_naam") or "").strip()
            if not naam or naam == "0":
                continue
            rec = per_gebied.setdefault(naam, {
                "gebied": naam, "afname": 0, "opwek": 0,
                "wachtrij_afname": a.get("wachtrij_afname"),
                "wachtrij_invoeding": a.get("wachtrij_invoeding"),
                "rnb": a.get("RNB"),
            })
            rec["afname"] = max(rec["afname"], a.get("afname") or 0)
            rec["opwek"] = max(rec["opwek"], a.get("opwek") or 0)

        # Sorteer: zwaarste netcongestie (afname) bovenaan.
        resultaat[gemeente] = sorted(per_gebied.values(),
                                     key=lambda x: -(x["afname"] or 0))
    return resultaat


if __name__ == "__main__":
    data = haal_netcongestie(["Den Haag", "Utrecht", "Almere"])
    for g, rijen in data.items():
        print(f"\n{g}: {len(rijen)} voedingsgebied(en)")
        for r in rijen:
            print(f"  {r['gebied']:<45} afname={label(r['afname'])}  "
                  f"wachtrij={r['wachtrij_afname']} MW  ({r['rnb']})")
