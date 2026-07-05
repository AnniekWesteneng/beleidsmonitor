"""Permanente opslag van de volglijst in de GitHub-repository.

Zowel het (online) dashboard als de automatische meldingen-taak gebruiken
dezelfde volglijst. Het dashboard draait op Streamlit Cloud, waar het lokale
bestandssysteem tijdelijk is; door de volglijst naar GitHub te schrijven (en
daarvan te lezen) is er één permanente bron die beide delen zien.

De schrijfsleutel (een fijnmazige GitHub-token met 'contents: write' op alleen
deze repo) staat NOOIT in de code, maar in de Streamlit-secrets of de omgeving:
    GITHUB_TOKEN=...
Optioneel te overschrijven: GITHUB_REPO (default 'AnniekWesteneng/beleidsmonitor')
en GITHUB_BRANCH (default 'main').

Zonder token valt alles terug op het lokale bestand volglijst.json, zodat het
lokaal blijft werken.
"""
import base64
import json
import os
from pathlib import Path

import requests

BESTAND = "volglijst.json"
_LOKAAL = str(Path(__file__).resolve().parent / BESTAND)
_API = "https://api.github.com"


def _conf(naam: str, default=None):
    """Lees een instelling uit de omgeving of uit Streamlit-secrets."""
    val = os.environ.get(naam)
    if val:
        return val
    try:
        import streamlit as st
        v = st.secrets.get(naam)
        if v:
            return v
    except Exception:
        pass
    return default


def heeft_token() -> bool:
    return bool(_conf("GITHUB_TOKEN"))


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _lees_lokaal() -> list:
    try:
        with open(_LOKAAL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _schrijf_lokaal(lijst: list) -> None:
    try:
        with open(_LOKAAL, "w", encoding="utf-8") as f:
            json.dump(lijst, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _github_get(token, repo, branch):
    """Haal de volglijst + sha op van GitHub. (lijst, sha) of (None, None) bij fout;
    ([], None) als het bestand nog niet bestaat."""
    url = f"{_API}/repos/{repo}/contents/{BESTAND}"
    try:
        r = requests.get(url, headers=_headers(token),
                         params={"ref": branch}, timeout=15)
    except Exception:
        return None, None
    if r.status_code == 200:
        data = r.json()
        try:
            inhoud = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(inhoud or "[]"), data.get("sha")
        except Exception:
            return None, None
    if r.status_code == 404:
        return [], None
    return None, None


def lees_volglijst() -> list:
    """Lees de volglijst — bij voorkeur van GitHub (permanent), anders lokaal."""
    token = _conf("GITHUB_TOKEN")
    if token:
        lijst, _ = _github_get(
            token, _conf("GITHUB_REPO", "AnniekWesteneng/beleidsmonitor"),
            _conf("GITHUB_BRANCH", "main"))
        if lijst is not None:
            _schrijf_lokaal(lijst)          # lokale spiegel bijwerken
            return lijst
    return _lees_lokaal()


def schrijf_volglijst(lijst: list) -> str:
    """Bewaar de volglijst. Retourneert een status:
    'github' = permanent opgeslagen (zichtbaar voor de meldingen),
    'lokaal' = alleen lokaal (geen token ingesteld),
    'fout'   = schrijven naar GitHub mislukt.
    """
    _schrijf_lokaal(lijst)                  # altijd de lokale kopie bijwerken
    token = _conf("GITHUB_TOKEN")
    if not token:
        return "lokaal"

    repo = _conf("GITHUB_REPO", "AnniekWesteneng/beleidsmonitor")
    branch = _conf("GITHUB_BRANCH", "main")
    _, sha = _github_get(token, repo, branch)   # huidige sha nodig om te overschrijven

    url = f"{_API}/repos/{repo}/contents/{BESTAND}"
    body = {
        "message": "Volglijst bijgewerkt via dashboard",
        "content": base64.b64encode(
            json.dumps(lijst, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha
    try:
        r = requests.put(url, headers=_headers(token), json=body, timeout=15)
        return "github" if r.status_code in (200, 201) else "fout"
    except Exception:
        return "fout"
