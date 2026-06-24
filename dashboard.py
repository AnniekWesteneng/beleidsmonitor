"""Laag 4 — Tonen: Streamlit-dashboard (Today Development-huisstijl).

Draaien:  streamlit run dashboard.py

HUISSTIJL AANPASSEN:
- Kleuren: pas BRAND hieronder + .streamlit/config.toml aan.
- Logo: zet je logobestand neer als  assets/logo.png  (of .svg) — het wordt
  dan automatisch in de koptekst getoond.
"""
import base64
import os
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from database import DB_PATH
from config import INDICATOREN, GEMEENTEN, PROVINCIES, GEMEENTE_PROVINCIE
from bronnen import netcongestie as nc
from bronnen import omgevingsloket as olo
from bronnen import kadaster as kad


def _secret(naam, default=None):
    """Lees een waarde uit Streamlit-secrets (cloud); val terug op default."""
    try:
        return st.secrets[naam]
    except Exception:
        return default

# --- Huisstijl Today Development -------------------------------------------
# Afgeleid van hun logo: donkere tekst ("TODAY" groot, "REAL ESTATE DEVELOPMENT"
# klein) op een zachte pastel-gradient (lila/paars -> perzik -> crème).
BRAND = {
    "tekst": "#1A1A1A",        # logo-/koptekst (bijna zwart)
    "grad1": "#9B93C9",        # lavendel/paars (linksboven in het logo)
    "grad2": "#DDA68E",        # koraal/perzik (rechtsboven)
    "grad3": "#FBF1E6",        # crème (onder)
    "accent": "#7E73B0",       # gedempt paars (slider/links/randjes)
    "licht": "#FAF4EC",        # kaartachtergrond (crème-tint)
}
ASSETS = Path(__file__).resolve().parent / "assets"

# Koppel indicator-ID aan de betekenis, zodat we de naam tonen i.p.v. "indicator 2".
INDICATOR_NAAM = {i["id"]: i["naam"] for i in INDICATOREN}


def indicator_label(indicator_id) -> str:
    try:
        nr = int(indicator_id)
    except (TypeError, ValueError):
        return "Geen indicator"
    naam = INDICATOR_NAAM.get(nr)
    return f"{nr}. {naam}" if naam else f"Indicator {nr}"


st.set_page_config(page_title="Beleidsmonitor · Today Development",
                   page_icon="📍", layout="wide")

# API-sleutel uit Streamlit-secrets (cloud) overnemen naar de omgeving, zodat de
# chat ook online werkt. Lokaal blijft .env gewoon werken.
_api = _secret("ANTHROPIC_API_KEY")
if _api:
    os.environ["ANTHROPIC_API_KEY"] = _api
_dso = _secret("DSO_PRE_API_KEY")
if _dso:
    os.environ["DSO_PRE_API_KEY"] = _dso
_dso_prod = _secret("DSO_PROD_API_KEY")
if _dso_prod:
    os.environ["DSO_PROD_API_KEY"] = _dso_prod
_rp = _secret("RUIMTELIJKE_PLANNEN_API_KEY")
if _rp:
    os.environ["RUIMTELIJKE_PLANNEN_API_KEY"] = _rp


def _wachtwoord_ok() -> bool:
    """Wachtwoord-slot. Is er geen wachtwoord ingesteld (bv. lokaal), dan open.
    Online (Streamlit Cloud) zet je 'app_wachtwoord' in de secrets."""
    juist = _secret("app_wachtwoord")
    if not juist:
        return True  # geen wachtwoord ingesteld -> vrij toegankelijk
    if st.session_state.get("auth_ok"):
        return True
    # Net, gecentreerd inlogscherm. Een form checkt pas bij verzenden (niet bij
    # elke toetsaanslag), wat het 'flitsen' tegengaat.
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("#### 🔒 Beveiligde toegang")
        with st.form("login_form", clear_on_submit=False, border=True):
            ingevoerd = st.text_input("Wachtwoord", type="password")
            verzonden = st.form_submit_button("Inloggen", use_container_width=True)
        if verzonden:
            if ingevoerd == juist:
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Onjuist wachtwoord.")
    return False


def _logo_html() -> str:
    """Toon het logo als assets/logo.png|svg bestaat; anders een woordmerk."""
    for naam, mime in [("logo.svg", "image/svg+xml"), ("logo.png", "image/png"),
                       ("logo.jpg", "image/jpeg")]:
        pad = ASSETS / naam
        if pad.exists():
            data = base64.b64encode(pad.read_bytes()).decode()
            return f'<img src="data:{mime};base64,{data}" style="height:44px;">'
    # Terugval: tekstueel woordmerk in de stijl van hun logo — "TODAY" in een
    # elegant schreef-lettertype, ondertitel in dunne, gespatieerde letters.
    return (f'<div style="line-height:1;color:{BRAND["tekst"]};">'
            '<div style="font-family:Georgia,\'Times New Roman\',serif;'
            'font-size:2.3rem;font-weight:700;letter-spacing:1px;">TODAY</div>'
            '<div style="font-size:.68rem;font-weight:400;letter-spacing:4px;'
            'opacity:.8;margin-top:2px;">REAL ESTATE DEVELOPMENT</div></div>')


# Huisstijl-CSS
st.markdown(f"""
<style>
  .block-container {{ padding-top: 3rem; }}
  .td-header {{
    background: linear-gradient(120deg, {BRAND['grad1']} 0%, {BRAND['grad2']} 55%, {BRAND['grad3']} 100%);
    border-radius: 12px; padding: 22px 30px; margin-bottom: 1.3rem;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .td-header .titel {{
    color: {BRAND['tekst']}; font-size: 1.15rem; font-weight: 700;
    text-align: right;
  }}
  .td-header .titel small {{ display:block; opacity:.65; font-weight:400; font-size:.8rem; }}
  div[data-testid="stMetric"] {{
    background: {BRAND['licht']}; border-radius: 10px; padding: 14px 16px;
    border-left: 4px solid {BRAND['accent']};
  }}
</style>
<div class="td-header">
  <div>{_logo_html()}</div>
  <div class="titel">Beleidsmonitor industrieel vastgoed
    <small>Signalen uit gemeentelijk &amp; provinciaal beleid</small></div>
</div>
""", unsafe_allow_html=True)

# Wachtwoord-slot (alleen actief als er online een wachtwoord is ingesteld).
if not _wachtwoord_ok():
    st.stop()

conn = sqlite3.connect(DB_PATH)
try:
    df = pd.read_sql("SELECT * FROM signalen", conn)
except Exception:
    df = pd.DataFrame()

if df.empty:
    st.info("Nog geen signalen in de database. Draai eerst de pipeline:  "
            "`python pipeline.py`")
    st.stop()

# Zorg dat nieuwere kolommen bestaan, ook als de database nog niet gemigreerd is.
for _kol in ["citaat", "pagina", "relevantie"]:
    if _kol not in df.columns:
        df[_kol] = None

# Hulpkolommen
df["_datum"] = pd.to_datetime(df["datum"], errors="coerce")
df["_zoektekst"] = (df["titel"].fillna("") + " " + df["samenvatting"].fillna("")
                    + " " + df["onderbouwing"].fillna("")).str.lower()
# Documentsleutel: gelijke url = zelfde document (anders op titel terugvallen).
df["_doc"] = df["url"].where(df["url"].astype(bool), df["titel"])

# Niveau (gemeente vs provincie) en bijbehorende provincie afleiden.
# Provincienamen die GEEN gemeente zijn = provinciaal-niveau signalen.
_PURE_PROVINCIES = set(PROVINCIES) - set(GEMEENTE_PROVINCIE)
df["_niveau"] = df["gemeente"].apply(
    lambda g: "provincie" if g in _PURE_PROVINCIES else "gemeente")
df["_provincie"] = df["gemeente"].apply(
    lambda g: g if g in _PURE_PROVINCIES else GEMEENTE_PROVINCIE.get(g, "Overig"))


def relevantie_sterren(waarde) -> str:
    try:
        n = int(waarde)
    except (TypeError, ValueError):
        return "—"
    return "★" * n + "☆" * (5 - n)


# --- Filters in de zijbalk ---
with st.sidebar:
    st.header("Filters")
    zoek = st.text_input("🔍 Zoeken", placeholder="bv. netcongestie, Binckhorst")

    prov_opties = sorted(df["_provincie"].dropna().unique())
    prov_sel = st.multiselect("Provincie", prov_opties, default=prov_opties)
    # Gemeenten (geen provinciaal niveau) binnen de gekozen provincie(s).
    gem_opties = sorted(df.loc[(df["_niveau"] == "gemeente") &
                               (df["_provincie"].isin(prov_sel)), "gemeente"].dropna().unique())
    gem = st.multiselect("Gemeente", gem_opties, default=gem_opties)
    cls = st.multiselect("Classificatie", ["kans", "risico", "contextafhankelijk"],
                         default=["kans", "risico", "contextafhankelijk"])

    aantal_per_ind = df.indicator_id.dropna().astype(int).value_counts().to_dict()
    ind_opties = {f"{indicator_label(i['id'])}  ({aantal_per_ind.get(i['id'], 0)})": i["id"]
                  for i in INDICATOREN}
    ind_sel_labels = st.multiselect("Indicator", list(ind_opties.keys()),
                                    default=list(ind_opties.keys()))
    ind_sel_ids = [ind_opties[l] for l in ind_sel_labels]

    min_rel = st.slider("Minimale relevantie (★)", 1, 5, 4,
                        help="Standaard 4: alleen sterke signalen. Zet op 1 om alles te zien.")

    # Datumbereik
    geldige = df["_datum"].dropna()
    van = tot = None
    if not geldige.empty:
        dmin, dmax = geldige.min().date(), geldige.max().date()
        keuze = st.date_input("Periode", value=(dmin, dmax),
                              min_value=dmin, max_value=dmax)
        if isinstance(keuze, (tuple, list)) and len(keuze) == 2:
            van, tot = keuze
        else:
            van, tot = dmin, dmax

    sorteer = st.selectbox("Sorteren op",
                           ["Relevantie (hoog → laag)", "Relevantie (laag → hoog)",
                            "Datum (nieuw → oud)", "Gemeente (A → Z)"])

# --- Filteren ---
mask = (
    df["_provincie"].isin(prov_sel)
    & (df.gemeente.isin(gem) | (df["_niveau"] == "provincie"))
    & df.classificatie.isin(cls)
    & df.indicator_id.isin(ind_sel_ids)
    & (df.relevantie.fillna(0) >= min_rel)
)
if zoek:
    mask &= df["_zoektekst"].str.contains(zoek.lower(), regex=False, na=False)
if van and tot:
    d = df["_datum"]
    mask &= d.isna() | ((d.dt.date >= van) & (d.dt.date <= tot))

filtered = df[mask]

kleuren = {"kans": "🟢", "risico": "🔴", "contextafhankelijk": "🟠"}


@st.cache_data(ttl=3600, show_spinner=False)
def _netcongestie(gemeenten_tuple):
    return nc.haal_netcongestie(list(gemeenten_tuple))


def _analyseer_adres(adres):
    """Analyseer een adres; cache alleen GESLAAGDE resultaten (een mislukte
    AI-duiding wordt niet bewaard, zodat een volgende poging het opnieuw probeert)."""
    from locatie_analyse import analyseer_adres
    cache = st.session_state.setdefault("_adres_cache", {})
    if adres in cache:
        return cache[adres]
    res = analyseer_adres(adres)
    gelukt = not res.get("fout") and not (res.get("duiding") or {}).get("fout")
    if gelukt:
        cache[adres] = res
    return res


tab_signalen, tab_net, tab_adres, tab_chat = st.tabs(
    ["📋 Signalen", "🔌 Netcongestie", "📍 Zoek op adres", "💬 Vraag de monitor"])

# =========================== TAB 1: SIGNALEN ================================
with tab_signalen:
    if filtered.empty:
        st.warning("Geen signalen die aan de filters voldoen. "
                   "Versoepel de filters in de zijbalk.")
    else:
        agg = filtered.groupby("_doc").agg(
            max_rel=("relevantie", "max"),
            datum=("_datum", "max"),
            gemeente=("gemeente", "first"),
        ).reset_index()

        if "laag → hoog" in sorteer:
            agg = agg.sort_values("max_rel", ascending=True, na_position="last")
        elif sorteer.startswith("Datum"):
            agg = agg.sort_values("datum", ascending=False, na_position="last")
        elif sorteer.startswith("Gemeente"):
            agg = agg.sort_values(["gemeente", "max_rel"], ascending=[True, False])
        else:  # Relevantie (hoog → laag)
            agg = agg.sort_values("max_rel", ascending=False, na_position="last")

        # Eén kaart per document, met alle indicator-signalen erin.
        for _, doc in agg.iterrows():
            rijen = filtered[filtered["_doc"] == doc["_doc"]].sort_values(
                "relevantie", ascending=False, na_position="last")
            eerste = rijen.iloc[0]
            dots = "".join(dict.fromkeys(kleuren.get(c, "⚪") for c in rijen.classificatie))
            sterren = relevantie_sterren(doc["max_rel"])
            with st.expander(f"{dots} {sterren} {eerste.titel} — {eerste.gemeente}"):
                st.caption(f"{eerste.documenttype} · {eerste.datum} · {eerste.bron} "
                           f"· {len(rijen)} signaal/signalen")
                for _, r in rijen.iterrows():
                    kleur = kleuren.get(r.classificatie, "⚪")
                    st.markdown(f"{kleur} **{indicator_label(r.indicator_id)}** — "
                                f"{r.classificatie or '–'} · {relevantie_sterren(r.relevantie)}")
                    if r.samenvatting:
                        st.write(r.samenvatting)
                    if r.onderbouwing:
                        st.caption(r.onderbouwing)
                    if pd.notna(r.citaat) and str(r.citaat).strip():
                        pag = ""
                        if pd.notna(r.pagina):
                            try:
                                pag = f" (pagina {int(r.pagina)})"
                            except (TypeError, ValueError):
                                pag = ""
                        st.caption(f"📄 Vindplaats{pag}: «{str(r.citaat).strip()}»")
                if eerste.url:
                    st.link_button("Bron openen", eerste.url)

# ========================== TAB: NETCONGESTIE ==============================
with tab_net:
    st.markdown("Live transportcapaciteit van het elektriciteitsnet per "
                "**voedingsgebied** (netvlak rond een onderstation). "
                "**Afname** = stroom afnemen (verbruik) · **Teruglevering** = "
                "terugleveren (bv. zon-op-dak). Bron: capaciteitskaart Netbeheer "
                "Nederland.")
    st.caption("🟢 ruim · 🟡 beperkt · 🟠 in onderzoek (wachtrij) · 🔴 tekort "
               "(wachtrij). Wachtrij = openstaande aanvragen in MW.")
    st.info("ℹ️ De koppeling gemeente ↔ voedingsgebied gebeurt op **naam** "
            "(vereenvoudiging). Voor het exacte, geografische beeld — inclusief de "
            "TenneT-hoogspanningslaag — is de officiële kaart leidend (knop onderaan).")
    # Beweeg mee met het gemeentefilter in de zijbalk (alleen geselecteerde
    # gemeenten tonen) — voorkomt een eindeloze lijst bij veel gemeenten.
    net_gemeenten = [g for g in GEMEENTEN if g in gem]
    if not net_gemeenten:
        st.warning("Selecteer in de zijbalk minstens één gemeente om de "
                   "netstatus te zien.")
    else:
        netdata = _netcongestie(tuple(net_gemeenten))
        for g in net_gemeenten:
            st.subheader(g)
            rijen = netdata.get(g, [])
            if not rijen:
                st.write("Geen netgegevens gevonden voor deze gemeente.")
                continue
            tabel_net = pd.DataFrame([{
                "Voedingsgebied": r["gebied"],
                "Afname": nc.label(r["afname"]),
                "Teruglevering": nc.label(r["opwek"]),
                "Wachtrij afname (MW)": r["wachtrij_afname"],
                "Wachtrij invoeding (MW)": r["wachtrij_invoeding"],
                "Netbeheerder": r["rnb"],
            } for r in rijen])
            st.dataframe(tabel_net, hide_index=True, use_container_width=True)
    st.link_button("Open de officiële capaciteitskaart", nc.KAART_URL)

# ========================= TAB: ZOEK OP ADRES ==============================
with tab_adres:
    st.markdown("Typ een adres → het **perceel**, de **geldende regels** op die locatie "
                "(uit het DSO/Omgevingsloket) en een **AI-duiding van kansen en risico's** "
                "voor industrieel vastgoed, plus onze eigen signalen voor die gemeente.")
    st.caption("ℹ️ DSO-data komt uit de productieomgeving van het Omgevingsloket "
               "(echte, geldende regels). De kans/risico-duiding is een AI-interpretatie "
               "van die regels; het omgevingsplan zelf blijft leidend.")
    adres = st.text_input("Adres", placeholder="bv. Atoomweg 50, Utrecht")
    if adres:
        with st.spinner("Adres opzoeken, DSO bevragen en analyseren…"):
            res = _analyseer_adres(adres)
        loc = res.get("locatie")
        if not loc:
            st.warning(res.get("fout", "Adres niet gevonden."))
        else:
            st.markdown(f"📍 **{loc.get('weergavenaam')}** — gemeente {loc.get('gemeente')}")

            # Eindoordeel in één oogopslag: gekleurde balk bovenaan.
            _d = res.get("duiding") or {}
            _g = _d.get("geschiktheid")
            _kern = _d.get("kernpunt", "")
            if _g == "geschikt":
                st.success(f"🟢 **Interessant voor industrieel vastgoed** — {_kern}")
            elif _g == "mits_voorwaarden":
                st.warning(f"🟠 **Mogelijk interessant, mits voorwaarden** — {_kern}")
            elif _g == "ongeschikt":
                st.error(f"🔴 **Weinig kansrijk voor industrieel vastgoed** — {_kern}")
            _pr = res.get("planregels") or {}
            _vbs = res.get("voorbereidingsbesluiten", [])
            for _v in _vbs:
                st.warning(f"⚠️ **Voorbereidingsbesluit van kracht** — {_v.get('naam')}")
            # Actualiteits-check via DSO: is de planologie hier in beweging?
            if _vbs:
                st.caption("🔎 DSO-actualiteitscheck: er loopt een voorbereidingsbesluit "
                           "— de onderstaande bestemmingsplan-waarden kunnen worden "
                           "gewijzigd. Bekijk de actuele/leidende regels via de knop onderaan.")
            else:
                st.caption("🔎 DSO-actualiteitscheck: geen voorbereidingsbesluit op dit "
                           "punt — de bestemmingsplan-waarden zijn naar verwachting "
                           "actueel. 'Regels op de kaart' blijft leidend.")

            # Harde planologische feiten op dit punt (Ruimtelijke Plannen).
            _best = _pr.get("bestemmingen", [])
            _maat = _pr.get("maatvoeringen", [])
            _func = _pr.get("functieaanduidingen", [])
            if _best or _maat or _func:
                st.markdown("**🏗️ Planologische feiten op dit punt**")
                if _best:
                    st.markdown("**Bestemming:** " + ", ".join(
                        b["naam"] for b in _best if b.get("naam")))
                if _maat:
                    cols = st.columns(min(len(_maat), 4))
                    for i, m in enumerate(_maat[:4]):
                        cols[i].metric(m.get("naam", "").replace(" (m)", "").replace(
                            " (%)", ""), m.get("waarde", "?"))
                if _func:
                    st.markdown("**Toegestane functie/categorie:** " + ", ".join(_func))
                st.caption("Bron: bestemmingsplan (nu het tijdelijk deel van het "
                           "omgevingsplan) via de Ruimtelijke Plannen — harde brondata, "
                           "geen AI. Ná 2024 vastgestelde omgevingsplan-wijzigingen "
                           "kunnen afwijken; 'Regels op de kaart' is leidend.")

            # Kadastraal perceel (Kadaster open data via PDOK) op deze locatie.
            kres = kad.perceel_op_locatie(loc["rd_x"], loc["rd_y"])
            p = kres.get("perceel")
            if p:
                opp = p.get("oppervlakte_m2")
                opp_txt = f"{opp:,.0f} m²".replace(",", ".") if opp else "onbekend"
                st.subheader("Kadastraal perceel")
                st.markdown(f"🗺️ **{p['aanduiding']}** — oppervlakte **{opp_txt}**")
                st.caption("Bron: Kadastrale Kaart (Kadaster open data via PDOK). "
                           "Toont perceel en omvang; eigendomsgegevens (BRK) zijn "
                           "betaald en niet opgenomen.")
                k1, k2 = st.columns(2)
                k1.link_button("🔎 Eigendomsinformatie opvragen (Kadaster, betaald)",
                               "https://www.kadaster.nl/producten/woning/eigendomsinformatie")
                k2.link_button("🏢 Bekijk in BAG-viewer (gratis)",
                               "https://bagviewer.kadaster.nl/")
                st.caption(f"De naam van de eigenaar is privacygevoelig (AVG) en niet "
                           f"automatisch op te halen. Via de Kadaster-knop vraag je voor "
                           f"perceel **{p['aanduiding']}** een eigendomsafschrift aan "
                           f"(~€2,85 per afschrift).")
            else:
                st.caption(f"Kadaster: {kres.get('fout', 'geen perceel gevonden')}")

            if res.get("fout"):
                st.info(f"DSO: {res['fout']}")
            else:
                d = res.get("duiding") or {}
                if d.get("fout"):
                    st.info(d["fout"])
                else:
                    # Kort & precies: wat moet je weten over dit perceel.
                    st.markdown("**📌 Wat geldt hier — om te weten vóór ontwikkeling**")
                    for punt in d.get("let_op", []) or ["—"]:
                        st.markdown(f"- {punt}")
                    with st.expander("🟢 Kansen & 🔴 risico's"):
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            st.markdown("**🟢 Kansen**")
                            for k in d.get("kansen", []) or ["—"]:
                                st.markdown(f"- {k}")
                        with dc2:
                            st.markdown("**🔴 Risico's**")
                            for rsk in d.get("risicos", []) or ["—"]:
                                st.markdown(f"- {rsk}")
                    if not (res.get("planregels") or {}).get("bestemmingen"):
                        st.caption("ℹ️ Voor dit punt is geen digitale bestemming "
                                   "gevonden in de Ruimtelijke Plannen; de duiding is "
                                   "dan o.b.v. de thema's. Bekijk de bestemming via de "
                                   "knop hieronder.")
                st.caption("De planologische feiten komen uit de Ruimtelijke Plannen / "
                           "het omgevingsplan; de duiding is een AI-interpretatie. Voor "
                           "de volledige context en kaart: open 'Regels op de kaart'.")
            st.link_button("📖 Bekijk de actuele, leidende regels bij de bron "
                           "(Regels op de kaart) — zoek op het adres",
                           "https://omgevingswet.overheid.nl/regels-op-de-kaart/")

            # Onze eigen signalen voor de gemeente van dit adres.
            bag = loc.get("gemeente") or ""
            ons_gem = {"'s-Gravenhage": "Den Haag"}.get(bag, bag)
            eigen = df[df.gemeente == ons_gem]
            st.subheader(f"Onze signalen in {ons_gem} "
                         f"({eigen['_doc'].nunique()} documenten)")
            if eigen.empty:
                st.write("Geen signalen voor deze gemeente in de database.")
            else:
                top = eigen.sort_values("relevantie", ascending=False,
                                        na_position="last").head(5)
                for _, r in top.iterrows():
                    kl = kleuren.get(r.classificatie, "⚪")
                    st.markdown(f"{kl} **{indicator_label(r.indicator_id)}** — "
                                f"{r.titel[:60]}")
                st.caption("Zie het tabblad Signalen voor alle signalen + filters.")

# ============================= TAB 2: CHAT ==================================
with tab_chat:
    import chat as chatmodule

    st.markdown("Stel een vraag in gewone taal. De chat antwoordt op basis van de "
                "signalen die nú door je filters komen.")
    st.caption(f"Kennisbasis: {filtered['_doc'].nunique()} documenten / {len(filtered)} "
               "signalen. ⚠️ Elke vraag kost een paar cent API-tegoed.")

    model_label = st.selectbox("Model", list(chatmodule.MODELLEN.keys()), index=0)

    if "chatgeschiedenis" not in st.session_state:
        st.session_state.chatgeschiedenis = []

    # Toon de gesprekgeschiedenis.
    for m in st.session_state.chatgeschiedenis:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    vraag = st.chat_input("Bv. Wat zijn de grootste risico's in Den Haag?")
    if vraag:
        with st.chat_message("user"):
            st.markdown(vraag)
        st.session_state.chatgeschiedenis.append({"role": "user", "content": vraag})

        with st.chat_message("assistant"):
            with st.spinner("Aan het nadenken…"):
                # Context: de meest relevante signalen binnen de huidige selectie.
                top = filtered.sort_values("relevantie", ascending=False, na_position="last").head(50)
                context = "\n".join(
                    f"- [{r.gemeente}] indicator {r.indicator_id} ({r.classificatie}, "
                    f"relevantie {r.relevantie}): {r.titel} — {r.samenvatting}"
                    for _, r in top.iterrows()
                ) or "(geen signalen in de huidige selectie)"
                try:
                    antwoord = chatmodule.beantwoord_vraag(
                        vraag, context, chatmodule.MODELLEN[model_label])
                except Exception as e:
                    antwoord = (f"⚠️ Er ging iets mis — waarschijnlijk geen API-tegoed "
                                f"of de sleutel ontbreekt.\n\n_Details: {e}_")
                st.markdown(antwoord)
        st.session_state.chatgeschiedenis.append({"role": "assistant", "content": antwoord})
