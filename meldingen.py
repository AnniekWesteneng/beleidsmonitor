"""Automatische e-mailmelding voor de volglijst-adressen.

Checkt per adres (via DSO / Ruimtelijke Plannen — GEEN AI, dus geen Anthropic-
tegoed) of er sinds de vorige run iets is veranderd: een nieuw voorbereidings-
besluit of een gewijzigde bestemming. Zo ja, dan gaat er één samenvattende
e-mail uit. Bedoeld om op een planning te draaien (zie .github/workflows/).

Toestand wordt bewaard in meldingen_state.json, zodat alleen ECHT nieuwe
wijzigingen een melding geven (de eerste run zet alleen de basislijn).
"""
import json
import os
import smtplib
from email.message import EmailMessage

from locatie_analyse import quick_check, vb_relevant

VOLG_PAD = "volglijst.json"
STATE_PAD = "meldingen_state.json"


def _laad(pad, default):
    try:
        with open(pad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _bewaar(pad, data):
    with open(pad, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _signatuur(qc: dict) -> dict:
    """Vergelijkbare 'toestand' van een adres."""
    return {
        # Alleen voor industrieel vastgoed relevante voorbereidingsbesluiten meetellen.
        "vb": sorted(v["naam"] for v in qc.get("voorbereidingsbesluiten", [])
                     if vb_relevant(v["naam"])),
        "bestemming": qc.get("bestemming", ""),
    }


def _verschillen(oud: dict, nieuw: dict) -> list[str]:
    meld = []
    nieuwe_vb = [v for v in nieuw["vb"] if v not in oud.get("vb", [])]
    if nieuwe_vb:
        meld.append("nieuw voorbereidingsbesluit: " + "; ".join(nieuwe_vb))
    if oud.get("bestemming") and oud["bestemming"] != nieuw["bestemming"]:
        meld.append(f"bestemming gewijzigd: '{oud['bestemming']}' -> "
                    f"'{nieuw['bestemming']}'")
    return meld


def _verstuur_mail(onderwerp: str, tekst: str):
    host = os.environ.get("SMTP_HOST")
    naar = os.environ.get("MELDING_NAAR")
    if not host or not naar:
        print("Geen SMTP_HOST/MELDING_NAAR ingesteld — mail overgeslagen.\n\n" + tekst)
        return
    msg = EmailMessage()
    msg["Subject"] = onderwerp
    msg["From"] = os.environ.get("MELDING_VAN") or os.environ.get("SMTP_USER", "")
    msg["To"] = naar
    msg.set_content(tekst)
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)
    print("E-mail verstuurd naar", naar)


def main():
    adressen = _laad(VOLG_PAD, [])
    state = _laad(STATE_PAD, {})
    meldingen = []
    for adr in adressen:
        qc = quick_check(adr)
        if qc.get("fout"):
            print(f"[overslaan] {adr}: {qc['fout']}")
            continue
        sig = _signatuur(qc)
        oud = state.get(adr)
        if oud is not None:                       # bestaand adres -> vergelijk
            diff = _verschillen(oud, sig)
            if diff:
                meldingen.append((adr, diff))
        else:
            print(f"[basislijn] {adr} toegevoegd aan toestand")
        state[adr] = sig
    _bewaar(STATE_PAD, state)

    if meldingen:
        tekst = "Wijzigingen op je volglijst (Beleidsmonitor):\n\n"
        for adr, diff in meldingen:
            tekst += f"- {adr}\n" + "".join(f"    * {d}\n" for d in diff) + "\n"
        tekst += ("\nBekijk de details in het dashboard of via 'Regels op de kaart'.")
        _verstuur_mail(f"Beleidsmonitor: {len(meldingen)} wijziging(en) op je volglijst",
                       tekst)
        print(tekst)
    else:
        print(f"Geen wijzigingen ({len(adressen)} adressen gecontroleerd).")


if __name__ == "__main__":
    main()
