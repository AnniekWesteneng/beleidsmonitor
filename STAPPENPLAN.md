# Stappenplan — Bouw van de Beleidsmonitor (reproduceerbaar)

Dit document beschrijft stap voor stap, en mét code, hoe de beleidsmonitor van
Today Development is gebouwd. Het is bedoeld als technische verantwoording/
bijlage en als reproductiehandleiding.

**Wat is het?** Een systeem dat Nederlandse gemeentelijke/provinciale
beleidsinformatie ophaalt, met AI toetst aan 10 beleidsindicatoren voor
industrieel vastgoed, en de resultaten toont in een dashboard.

**Hulpmiddelen:** gebouwd met Claude Code (Anthropic). Classificatie in de app
gebruikt het model Claude Sonnet 4.6. Programmeertaal: Python 3.12.

---

## 0. Architectuur (4 lagen)

1. **Ophalen** — Python-scripts roepen de open API's van de bronnen aan.
2. **Verwerken** — tekst uit XML/HTML/PDF extraheren en opschonen.
3. **Classificeren** — elk document via de Claude API toetsen aan 10 indicatoren.
4. **Opslaan + tonen** — resultaten in SQLite, getoond in een Streamlit-dashboard.

**Techniekkeuze (bewust simpel):** Python 3.12 · SQLite (één bestand, geen
server) · `requests` · `anthropic` (officiële SDK) · Streamlit (dashboard) ·
`beautifulsoup4`/`lxml`/`pypdf` (tekstextractie).

Belangrijk principe: **klein beginnen** (1 bron, 3 gemeenten, lokaal) en daarna
opschalen. De architectuur is identiek voor 3 of 342 gemeenten — alleen een
configuratielijst verandert.

---

## 1. Projectopzet

```powershell
# Python installeren (eenmalig)
winget install --id Python.Python.3.12 --scope user

# In de projectmap: virtuele omgeving + packages
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt`:
```
requests
anthropic
streamlit
python-dotenv
beautifulsoup4
pandas
lxml
pypdf
```

`.env` (geheim, staat in `.gitignore`):
```
ANTHROPIC_API_KEY=sk-ant-...
```

Mapstructuur:
```
beleidsmonitor/
├── config.py            # gemeenten, indicatoren, instellingen
├── zoektermen.py        # zoektermenlijst
├── verwerk.py           # tekstextractie (laag 2)
├── classificeer.py      # AI-classificatie (laag 3)
├── chat.py              # chatfunctie
├── database.py          # SQLite opslag (laag 4)
├── pipeline.py          # zet alles aan elkaar
├── dashboard.py         # Streamlit-dashboard (laag 4)
└── bronnen/             # databronnen (laag 1)
    ├── officiele_bekendmakingen.py
    ├── open_raadsinformatie.py
    └── netcongestie.py
```

---

## 2. Configuratie (`config.py`)

Het hart: gemeenten + de 10 indicatoren + instellingen. Opschalen = deze lijsten
uitbreiden.

```python
GEMEENTEN = ["Den Haag", "Utrecht", "Almere"]
PROVINCIES = ["Zuid-Holland", "Utrecht", "Flevoland"]

INDICATOREN = [
    {"id": 1, "naam": "Transformatiedruk op industriële bestemming", "classificatie": "contextafhankelijk"},
    {"id": 2, "naam": "Beschikbaarheid en programmering bedrijventerrein", "classificatie": "kans"},
    {"id": 3, "naam": "Milieuruimte en milieuzonering", "classificatie": "contextafhankelijk"},
    {"id": 4, "naam": "Energie-infrastructuur en netcongestie", "classificatie": "contextafhankelijk"},
    {"id": 5, "naam": "Infrastructuur en logistieke bereikbaarheid", "classificatie": "contextafhankelijk"},
    {"id": 6, "naam": "Eigendomsstructuur en grondpositie", "classificatie": "contextafhankelijk"},
    {"id": 7, "naam": "Bouwregelgeving en exploitatierandvoorwaarden", "classificatie": "risico"},
    {"id": 8, "naam": "Functieverruiming op bestaande locatie", "classificatie": "kans"},
    {"id": 9, "naam": "Actief vestigingsbeleid en economische stimulering", "classificatie": "kans"},
    {"id": 10, "naam": "Vergunningstraject als projectrisico", "classificatie": "risico"},
]

from zoektermen import ZOEKTERMEN   # uitgebreide lijst, gegroepeerd per indicator
VANAF_JAAR = 2022            # alleen documenten vanaf dit jaar
INCLUSIEF_PROVINCIE = True   # provinciaal beleid meenemen
MAX_TEKST_TEKENS = 16000     # tekstlengte per document naar het AI-model
```

---

## 3. Werkwijze: eerst de bron verifiëren (methodologie)

Bij elke nieuwe bron is steeds **eerst de echte API geverifieerd** met een klein
testscript dat de ruwe respons toont — pas daarna is de verwerking gebouwd. Dus:
nooit blind vertrouwen op aannames over veldnamen of structuur. De
`bronnen/_verken_*.py`-scripts documenteren deze verificatie en vormen het bewijs.

Voorbeeld (vereenvoudigd): de ruwe SRU-respons ophalen en printen vóór parsing.
```python
import requests
params = {"operation": "searchRetrieve", "version": "2.0",
          "maximumRecords": "3",
          "query": '(c.product-area==officielepublicaties) and (cql.textAndIndexes="bedrijventerrein")'}
r = requests.get("https://repository.overheid.nl/sru", params=params, timeout=30)
print(r.text[:4000])   # bekijk de structuur, pas daarna de parsing aan
```

---

## 4. Bron 1: Officiële Bekendmakingen — SRU-API

**Geverifieerde feiten** (uit de verkenning):
- Endpoint: `https://repository.overheid.nl/sru`, querytaal CQL.
- Filteren op gemeente: `dt.creator="<naam>"`. Vrije tekst: `cql.textAndIndexes="<term>"`.
- Datumfilter + sorteren: `dt.date>="2022-01-01" sortBy dt.date/sort.descending`.
- Provincie/gemeente delen soms een naam (Utrecht); provinciale stukken zijn te
  herkennen aan publicatienaam 'Provinciaal blad'.
- 'Den Haag' staat onder twee creator-namen: 'Den Haag' én ''s-Gravenhage'.
- De dienst throttelt → retry-met-backoff ingebouwd.

Kern van de zoekopdracht:
```python
query = (f'({creator_clause}) and (cql.textAndIndexes="{zoekterm}") '
         f'and (dt.date>="{VANAF_JAAR}-01-01") sortBy dt.date/sort.descending')
```

De records leveren metadata + URLs (XML/HTML/PDF). De volledige tekst wordt
apart opgehaald (zie laag 2). Elke bron levert dezelfde interface aan de
pipeline: `BRON_NAAM`, `haal(gebied, zoekterm, max)`, `vul_tekst(doc)`.

---

## 5. Tekstextractie (`verwerk.py`, laag 2)

De documenttekst wordt opgehaald in volgorde **XML → HTML → PDF** (eerste die
lukt). Voor lange documenten wordt niet bot afgekapt, maar een **fragment rond de
zoekterm** geselecteerd, zodat relevante passages verderop niet wegvallen.

```python
def haal_documenttekst(xml_url=None, html_url=None, pdf_url=None, timeout=60):
    for url, soort in [(xml_url, "xml"), (html_url, "html"), (pdf_url, "pdf")]:
        if not url: continue
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200: continue
        tekst = extract(r.content, soort)   # bs4 (xml/html) of pypdf (pdf)
        if len(tekst) > 50: return tekst
    return ""
```

---

## 6. Classificatie (`classificeer.py`, laag 3)

Het indicatorenkader komt hier tot leven als systeeminstructie aan het model.
Belangrijke keuze: het model geeft **meerdere** indicatoren per document terug
(een document kan tegelijk een kans en een risico op verschillende indicatoren
bevatten) plus een **relevantiescore (1-5)**.

```python
MODEL = "claude-sonnet-4-6"

SYSTEEM_PROMPT = """Je bent een neutrale, feitelijke beleidsanalist voor Today
Development, een ontwikkelaar van industrieel vastgoed. Je beoordeelt of een
beleidsdocument signalen bevat die relevant zijn voor industrieel vastgoed, op
basis van 10 indicatoren.

DEFINITIES:
- KANS: vergroot/versterkt/versnelt de ontwikkelmogelijkheden.
- RISICO: beperkt, vertraagt of maakt onzeker.
- CONTEXTAFHANKELIJK: hangt af van type vastgoed (Layers = milieucategorie 3.2)
  en locatie.
- RELEVANTIE (1-5): hoe sterk en direct raakt het signaal de ontwikkelmogelijk-
  heden (5 = zeer sterk/concreet, 1 = marginaal).

Eén document kan MEERDERE indicatoren raken. Geef elk relevant signaal apart.
Antwoord UITSLUITEND met JSON:
{"signalen": [{"indicator_id": <1-10>, "classificatie": "kans"/"risico"/
"contextafhankelijk", "relevantie": <1-5>, "samenvatting": "...",
"onderbouwing": "..."}]}"""

def classificeer(titel, tekst, zoekterm=None):
    fragment = maak_fragment(tekst, zoekterm, limiet=MAX_TEKST_TEKENS)
    bericht = client.messages.create(model=MODEL, max_tokens=1500,
        system=SYSTEEM_PROMPT,
        messages=[{"role": "user", "content": f"Titel: {titel}\n\nTekst:\n{fragment}"}])
    return parse_signalen(bericht.content[0].text)   # gevalideerde lijst
```

---

## 7. Database (`database.py`, laag 4)

SQLite, één bestand. Eén document kan meerdere signalen opleveren, dus de
uniciteit ligt op **(url, indicator_id)** — niet op url alleen.

```python
CREATE TABLE IF NOT EXISTS signalen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gemeente TEXT, titel TEXT, documenttype TEXT, bron TEXT,
    datum TEXT, url TEXT,
    indicator_id INTEGER, classificatie TEXT, relevantie INTEGER,
    samenvatting TEXT, onderbouwing TEXT,
    opgehaald_op TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_url_indicator ON signalen(url, indicator_id);
```

`url_bestaat()` voorkomt dat een al verwerkt document opnieuw (en duur)
geclassificeerd wordt.

---

## 8. Pipeline (`pipeline.py`)

Zet de lagen aan elkaar en loopt over alle bronnen + gebieden (gemeenten, plus
provincies voor bronnen die dat ondersteunen).

```python
for bron in BRONNEN:                         # [officiele_bekendmakingen, open_raadsinformatie]
    gebieden = list(GEMEENTEN)
    if getattr(bron, "ONDERSTEUNT_PROVINCIES", False):
        gebieden += PROVINCIES
    for gebied in gebieden:
        for term in ZOEKTERMEN:
            for doc in bron.haal(gebied, term, max_per_term):
                if url_bestaat(conn, doc["url"]): continue     # bespaar kosten
                tekst = bron.vul_tekst(doc)
                if not tekst: continue
                for signaal in classificeer(doc["titel"], tekst, term):
                    sla_op(conn, {**doc, **signaal})
```

Draaien: `python pipeline.py`

---

## 9. Dashboard (`dashboard.py`, laag 4)

Streamlit-app met:
- **Drie tabbladen**: Signalen · Netcongestie · Chat.
- Filters in de zijbalk: gemeente, classificatie, bron, indicator, relevantie-
  schuifje (standaard ≥4), datumbereik, vrije-tekst zoeken, sorteren.
- Signalen **gegroepeerd per document** (één kaart met alle indicator-signalen).
- **Huisstijl** Today Development (pastel-gradient koptekst, woordmerk).
- **Wachtwoord-slot** + secrets voor de online versie.

Draaien: `streamlit run dashboard.py`

---

## 10. Bron 2: Open Raadsinformatie (Elasticsearch)

**Geverifieerd:** endpoint `https://api.openraadsinformatie.nl/v1/elastic`; per
gemeente een eigen index (`ori_utrecht*`, `ori_den_haag*`, `ori_almere*`);
volledige tekst zit in het veld `text` (lijst per pagina); datum = `last_discussed_at`.

```python
body = {"size": max, "query": {"bool": {
            "must": [{"simple_query_string": {"fields": ["text","title","name"],
                       "default_operator": "and", "query": zoekterm}}],
            "filter": {"range": {"last_discussed_at": {"gte": f"{VANAF_JAAR}-01-01"}}}}},
        "sort": [{"last_discussed_at": {"order": "desc"}}]}
requests.post(f"{BASE}/ori_{slug}*/_search", json=body)
```

---

## 11. Bron 3: Netcongestie (capaciteitskaart Netbeheer Nederland)

Geen documenten maar **live statusdata** (ArcGIS FeatureServer, open, geen
sleutel). Getoond als apart paneel, niet via de AI-classificatie.

**Geverifieerd:** afname-kaart gebruikt veld `afname`, teruglevering-kaart veld
`opwek`; codes 0-3 = beschikbaar/beperkt/in onderzoek/tekort (afgeleid uit de
officiële Arcade-formule). Granulariteit = voedingsgebied; gekoppeld aan gemeente
op naam (vereenvoudiging; geografische koppeling staat gepland).

```python
SERVICE = ".../Capaciteitskaart_elektriciteitsnet_v2_afname/FeatureServer/0/query"
params = {"where": f"voedingsgebied_naam LIKE '%{gemeente}%'", "outFields": "*",
          "f": "json", "returnGeometry": "false"}
```

---

## 12. Online zetten (Streamlit Community Cloud)

1. Code naar **GitHub** (privé of publiek) via GitHub Desktop.
2. App aanmaken op **share.streamlit.io**, hoofdbestand `dashboard.py`.
3. In **Settings → Secrets**:
   ```toml
   app_wachtwoord = "..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. De database (`beleidsmonitor.db`) gaat mee in de repo; de online versie is een
   etalage. Verzamelen (de pipeline) draait lokaal/elders.

---

## 13. Reproduceren (samengevat)

```powershell
# 1. omgeving
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# 2. API-sleutel in .env zetten
# 3. data verzamelen
.\.venv\Scripts\python.exe pipeline.py
# 4. dashboard tonen
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

---

## Verantwoording (kort)

De code is met Claude Code (Anthropic) geschreven op basis van mijn
specificaties; ik heb het indicatorenkader, de bronkeuze en alle ontwerp-
beslissingen bepaald, de databronnen geverifieerd (testscripts tegen echte
respons) en de AI-classificatie steekproefsgewijs gecontroleerd. Beperkingen
(AI-interpretatie, recall afhankelijk van zoektermen, vereenvoudigde geo-
koppeling) zijn expliciet benoemd. Ontwikkeling: juni 2026.
