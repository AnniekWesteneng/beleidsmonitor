# Beleidsmonitor — onboarding voor teamgenoten

Welkom! Dit project is de **Beleidsmonitor** van Today Development: een tool die
Nederlandse gemeentelijke/provinciale beleidsinformatie ophaalt, met AI
classificeert tegen 10 beleidsindicatoren voor industrieel vastgoed, en toont in
een Streamlit-dashboard. Deze gids helpt je snel meebouwen met Claude Code.

## Wat het doet (in het kort)
De tool heeft twee functies:
1. **Signalenfeed** — volgt beleid over de tijd via *Officiële Bekendmakingen* (SRU)
   en *Open Raadsinformatie*. Elk document wordt door Claude beoordeeld: kans /
   risico / contextafhankelijk / niet-relevant, tegen 10 indicatoren.
2. **Zoek op adres** — de geldende regels per locatie via *Omgevingsloket/DSO*,
   *Ruimtelijke Plannen* en de *Kadastrale Kaart (PDOK)*: bestemming, bouwhoogte,
   voorbereidingsbesluit, perceel — met een AI-eindoordeel en PDF-rapport.

Daarnaast: een netcongestie-kaart, een **volglijst met automatische
e-mailmeldingen**, en een chat om door te vragen over de signalen.

## Architectuur (4 lagen)
1. **Ophalen** — `bronnen/*.py` (elke bron een eigen module).
2. **Verwerken** — `verwerk.py` (tekst uit XML/HTML/PDF).
3. **Classificeren** — `classificeer.py` (Claude API, model `claude-haiku-4-5`).
4. **Opslaan + tonen** — `database.py` (SQLite: `beleidsmonitor.db`) + `dashboard.py`.

De `pipeline.py` koppelt de lagen: per gemeente/zoekterm ophalen → classificeren →
opslaan. Al verwerkte URLs worden overgeslagen (dedup), dus runs zijn hervatbaar.

## Belangrijkste bestanden
| Bestand | Rol |
|---|---|
| `config.py` | Gemeenten, provincies, indicatoren, zoektermen. Opschalen = deze lijst uitbreiden. |
| `classificeer.py` | De AI-systeemprompt + classificatielogica (het inhoudelijke hart). |
| `database.py` | SQLite-schema + opslag; uniciteit op (url, indicator_id). |
| `pipeline.py` / `run_gemeente.py` | De verwerkingspijplijn draaien. |
| `dashboard.py` | Het Streamlit-dashboard (tabs: Signalen, Netcongestie, Zoek op adres, Volglijst, Chat). |
| `locatie_analyse.py` | De adres-analyse (RP + DSO + Kadaster + AI-duiding + PDF). |
| `meldingen.py` | Volglijst-controle + e-mailmelding (draait via GitHub Actions). |
| `volglijst_opslag.py` | Bewaart de volglijst permanent in de GitHub-repo (dashboard schrijft, meldingen lezen). |
| `bronnen/` | De databronkoppelingen. `_verken_*.py` zijn verkenningsscripts (bewijs van bron-verificatie). |

## Opzetten (lokaal draaien)
1. **Python 3.12** en een virtuele omgeving:
   ```
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```
2. **Sleutels** in een `.env`-bestand (staat NIET in git — vraag Anniek om de waarden):
   ```
   ANTHROPIC_API_KEY=...
   DSO_PROD_API_KEY=...
   RUIMTELIJKE_PLANNEN_API_KEY=...
   ```
3. **Dashboard draaien:**
   ```
   streamlit run dashboard.py
   ```
4. **Nieuwe signalen ophalen** (kost AI-tegoed — begin klein):
   ```
   python run_gemeente.py "Utrecht"
   ```

## Belangrijke afspraken
- **Sleutels nooit in de code.** Ze horen alleen in `.env` (lokaal) en in de
  Streamlit-/GitHub-secrets. De repo is **openbaar**.
- **Documenttitels tonen we letterlijk** (inclusief typefouten) — dat is bewust,
  voor traceerbaarheid. Niet "corrigeren".
- **Klein testen voor breed draaien** — de classificatie kost per document tokens.
- De tool is een **startpunt/alarmsysteem**, geen vervanging van vakinhoudelijk
  oordeel. Zo ook presenteren.

## Online & automatisch
- Het dashboard draait online via **Streamlit Cloud** (beveiligd met wachtwoord).
- De **meldingen** draaien op schema via **GitHub Actions**
  (`.github/workflows/meldingen.yml`); die gebruiken de volglijst uit de repo.
- Nodig als secrets voor de meldingen: `SMTP_HOST/PORT/USER/PASS`, `MELDING_VAN`,
  `MELDING_NAAR`, plus de API-sleutels hierboven.

## Achtergrond / verantwoording
- `maak_verantwoording.py` genereert het verantwoordingsdocument (bijlage bij de
  scriptie): bronkeuzes, afwijkingen van het bouwplan, validatie.
- `UITBREIDINGSPLAN.md`, `STAPPENPLAN.md`, `DEPLOY.md` bevatten aanvullende context.

Veel succes — begin gerust met `config.py` en `dashboard.py` om het overzicht te krijgen.
