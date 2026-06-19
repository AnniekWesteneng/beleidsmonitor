"""Laag 2 — Verwerken: tekst uit documenten halen en opschonen.

De SRU-bron levert alleen metadata + URLs. Hier halen we de daadwerkelijke
documenttekst op (XML het schoonst, dan HTML, dan PDF) en schonen die op.
Ook bevat deze laag een 'slim fragment'-functie die voor lange documenten
de relevante passages rond een zoekterm selecteert, zodat het AI-model die
niet mist door afkapping.
"""
import io

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

HEADERS = {
    "User-Agent": "Beleidsmonitor-TodayDevelopment/0.1 (afstudeerproject; contact via Today Development)"
}


def schoon_tekst(tekst: str) -> str:
    """Normaliseer witruimte: meerdere spaties/regels -> enkele spatie."""
    return " ".join(tekst.split())


def extract_uit_xml(inhoud: bytes) -> str:
    soup = BeautifulSoup(inhoud, "lxml-xml")
    return schoon_tekst(soup.get_text(" ", strip=True))


def extract_uit_html(inhoud: bytes) -> str:
    soup = BeautifulSoup(inhoud, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return schoon_tekst(soup.get_text(" ", strip=True))


def extract_uit_pdf(inhoud: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(inhoud))
        delen = [(pagina.extract_text() or "") for pagina in reader.pages]
        return schoon_tekst(" ".join(delen))
    except Exception:
        return ""


def haal_documenttekst(xml_url: str | None = None,
                       html_url: str | None = None,
                       pdf_url: str | None = None,
                       timeout: int = 60) -> str:
    """Haal de volledige tekst van een document op.

    Probeert in volgorde: XML (schoonst) -> HTML -> PDF. Geeft een lege string
    terug als alles faalt.
    """
    for url, soort in [(xml_url, "xml"), (html_url, "html"), (pdf_url, "pdf")]:
        if not url:
            continue
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code != 200:
                continue
            if soort == "xml":
                r.encoding = "utf-8"
                tekst = extract_uit_xml(r.content)
            elif soort == "html":
                r.encoding = "utf-8"
                tekst = extract_uit_html(r.content)
            else:
                tekst = extract_uit_pdf(r.content)
            if len(tekst) > 50:  # zinnige inhoud gevonden
                return tekst
        except Exception:
            continue
    return ""


def maak_fragment(tekst: str, zoekterm: str | None = None,
                  limiet: int = 16000, venster: int = 2000) -> str:
    """Selecteer een representatief tekstfragment binnen 'limiet' tekens.

    Korte documenten worden volledig teruggegeven. Lange documenten worden niet
    bot afgekapt: we nemen het begin (titel/aanhef bevat vaak context) plus
    vensters rond de plekken waar de zoekterm voorkomt, zodat relevante passages
    verderop in het document toch worden meegenomen.
    """
    tekst = tekst or ""
    if len(tekst) <= limiet:
        return tekst

    # Altijd het begin meenemen (kop/aanhef/samenvatting).
    kop = tekst[: venster * 2]
    stukken = [kop]
    gebruikt = len(kop)

    if zoekterm:
        laag = tekst.lower()
        # Pak alle losse woorden uit de zoekterm (bv. "binnenplanse afwijking").
        woorden = [w for w in zoekterm.lower().split() if len(w) > 3] or [zoekterm.lower()]
        vondsten = []
        for w in woorden:
            start = 0
            while gebruikt < limiet:
                pos = laag.find(w, start)
                if pos == -1:
                    break
                vondsten.append(pos)
                start = pos + len(w)
        for pos in sorted(set(vondsten)):
            if gebruikt >= limiet:
                break
            van = max(0, pos - venster // 2)
            tot = min(len(tekst), pos + venster)
            fragment = tekst[van:tot]
            stukken.append(fragment)
            gebruikt += len(fragment)

    resultaat = " […] ".join(stukken)
    return resultaat[:limiet]


def _norm(t: str) -> str:
    return " ".join((t or "").lower().split())


def pdf_paginas(pdf_url: str | None, timeout: int = 60) -> list[str]:
    """Geef de (genormaliseerde) tekst per pagina van een PDF. Lege lijst als het
    geen PDF is of niet lukt."""
    if not pdf_url:
        return []
    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            return []
        reader = PdfReader(io.BytesIO(r.content))
        return [_norm(p.extract_text() or "") for p in reader.pages]
    except Exception:
        return []


def zoek_pagina(paginas: list[str], citaat: str) -> int | None:
    """Zoek op welke pagina (1-gebaseerd) het citaat voorkomt; None indien niet
    gevonden. Probeert aflopend kortere fragmenten voor robuustheid."""
    naald = _norm(citaat)
    if not paginas or len(naald) < 20:
        return None
    for lengte in (160, 90, 45):
        frag = naald[:lengte]
        if len(frag) < 20:
            continue
        for i, tekst in enumerate(paginas, start=1):
            if frag in tekst:
                return i
    return None
