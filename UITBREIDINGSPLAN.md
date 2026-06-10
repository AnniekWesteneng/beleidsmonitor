# Uitbreidingsplan — Beleidsmonitor Today Development

Dit document beschrijft hoe de beleidsmonitor kan groeien. Het is opgebouwd uit
**vier assen** (bronnen, zoekdiepte, geografie, techniek) plus drie thema's
(diepere analyse, meldingen, overige functies) en een gefaseerde routekaart.

Status bij schrijven: 2 bronnen, 3 gemeenten (Den Haag, Utrecht, Almere),
~1.300 signalen, online dashboard met wachtwoord.

---

## As 1 — Meer bronnen (breedte van informatie)

Per bron: welke indicator(en) hij vult, of de data open is, de waarde en de
bouwmoeite. Volgorde = aanbevolen prioriteit.

| Bron | Indicator(en) | Open data? | Waarde | Moeite |
|---|---|---|---|---|
| Provinciale bekendmakingen (KOOP/SRU) | 1, 2, 3, 9 | Ja (al binnen bereik) | Hoog | Laag |
| Netcongestie-capaciteitskaart (Netbeheer NL) | 4 | Ja (open kaart) | Hoog (nu blinde vlek) | Midden |
| IBIS Bedrijventerreinen (werklocatie-database) | 2 | Ja (via provincies) | Hoog | Midden |
| Omgevingsplannen — beslissingen | 3, 7, 8 | Ja (al via bekendmakingen) | Midden | Laag (al gedekt) |
| Omgevingsplannen — live status per locatie (DSO) | 3, 7, 8 | Ja, maar complex (geo) | Midden-hoog | Hoog |
| Kadaster — perceelgrenzen/adressen (PDOK/BAG) | 6 | Ja (gratis) | Laag-midden | Midden |
| Kadaster — eigendom (BRK) | 6 | Betaald + privacy-beperkt | Hoog | Hoog/€ |
| Omgevingsdiensten — milieuvergunningen | 3, 10 | Wisselend | Midden | Hoog |
| Gemeente-/provincienieuws (RSS) | breed (vroeg signaal) | Ja | Laag (veel ruis) | Laag |

**Nuances:**
- **Omgevingsplannen:** de *besluiten* (ontwerp/vaststelling/wijziging) komen al
  binnen via de Officiële Bekendmakingen. Wat ontbreekt is de *live status per
  locatie* — dat is geo-data (DSO) en past beter als locatie-opzoekfunctie.
- **Kadaster:** perceelgrenzen en adressen zijn gratis (PDOK/BAG), maar
  *eigendom* (wie bezit het) is betaald en privacy-beperkt.

**Quick wins:** provinciale bekendmakingen (lage moeite) en netcongestie-kaart
(vult indicator 4, nu het grootste gat).

**Werkwijze nieuwe bron:** eerst de echte API verkennen met een testscript, dan
pas parsing schrijven. Elke bron levert dezelfde interface: `BRON_NAAM`,
`haal(gebied, zoekterm, max)`, `vul_tekst(doc)`.

---

## As 2 — Dieper zoeken (zoekdiepte)

Hoe grondig de monitor zoekt, bepaalt of álle relevante signalen bovenkomen
(recall). Een ladder van ondiep+goedkoop naar diep+duur:

| Aanpak | Recall | Kosten | Wat het is |
|---|---|---|---|
| 1. Nu: trefwoorden + nieuwste N | matig | € | Top 6-10 recente docs per zoekterm. Snel, mist de staart. |
| 2. Dieper per zoekterm (doorbladeren) | redelijk | €€ | Alle treffers per term, niet alleen de nieuwste. |
| 3. Bredere trefwoorden + synoniemen | redelijk | € | Deels al gedaan (95 termen). |
| 4. Semantisch zoeken (embeddings) | hoog | €€ | Zoeken op betekenis i.p.v. woord; vangt docs zonder je trefwoorden. Vereist embeddingsmodel. |
| 5. Breed ophalen + AI-filter | maximaal | €€€ | Alle recente docs per gemeente ophalen, AI filtert. Hoogste recall, duurst. |
| 6. Volledige tekst i.p.v. fragment | diepte per doc | €€ | Lange documenten volledig in stukken laten lezen i.p.v. ~16.000 tekens. |
| 7. Verder terug in tijd | historisch | €€ | VANAF_JAAR verlagen → trends over meerdere jaren. |
| 8. Tweede AI-pass met sterker model (Opus) | diepte van oordeel | €€ | Topdocumenten extra grondig laten analyseren. |

**De grote drie keuzes:** 4 (semantisch) en 5 (breed + AI-filter) verhogen écht
de recall; 6/8 verdiepen de kwaliteit per document; 2/3/7 zijn graduele stappen.

---

## As 3 — Geografisch opschalen

De architectuur schaalt door de gemeentenlijst uit te breiden.

| Schaal | Eenmalige kosten* | Doorlooptijd** | Techniek |
|---|---|---|---|
| 3 gemeenten (nu) | — | — | huidige opzet |
| Regio (30-50 gemeenten) | €200-400 (zuinig €50-100) | uren | Haiku + planning |
| Provincie / Randstad | €400-800 | ~dag | Batch API |
| Heel NL (342) | €1.000-2.000 (zuinig €300-600) | dagen | Batch API + cloud |

*\*Ordegrootte, afhankelijk van model + documentaantal.* *\*\*Vooral door API-throttling.*

**Advies:** richt op de gemeenten waar Today actief is of wil zijn. Gericht
opschalen vangt ~95% van de relevante signalen tegen een fractie van de kosten.

---

## As 4 — Techniek die opschalen betaalbaar maakt

- Goedkoper classificeren: `claude-haiku-4-5` (~3× goedkoper), kortere tekst, prompt-caching.
- Batch API: ~50% goedkoper, gemaakt voor grote volumes.
- Automatische runs: wekelijks via Windows Taakplanner of GitHub Actions.
- Pipeline in de cloud: verzamelen hoeft niet op de eigen pc.

---

## Diepere analyse (wat je mét de data doet)

- Trendanalyse over tijd (neemt transformatiedruk/netcongestie toe?).
- Vergelijking tussen gemeenten (benchmark vestigingsklimaat).
- Verandering-detectie (alleen tonen wat nieuw is sinds vorige run).
- Cross-document synthese (beleidsrichting per gemeente samenvatten).
- Koppeling aan Today's portefeuille (signaal bij eigen locatie weegt zwaarder).

---

## Meldingen

**Waarover (trigger):**

| Trigger | Toelichting |
|---|---|
| Nieuw sterk risico (★4-5) | Alleen de belangrijke risico's; weinig ruis. |
| Nieuw signaal in "jouw" gemeente | Bv. waar Today actief is. |
| Nieuw signaal op een indicator | Bv. netcongestie (indicator 4). |
| Op een trefwoord | Opgeslagen zoekopdracht. |
| Statuswijziging | Plan van ontwerp → vastgesteld. |

**Hoe vaak:** direct (kan druk) · wekelijkse/dagelijkse samenvatting (aanbevolen)
· alleen bij iets belangrijks.

**Kanaal:**

| Kanaal | Geschikt? | Moeite |
|---|---|---|
| Microsoft Teams (webhook) | Top voor een bedrijf (Microsoft 365) | Laag |
| E-mail | Universeel | Laag-midden |
| In het dashboard ("Nieuw"-sectie) | Geen extern kanaal | Zeer laag / gratis |
| Slack | Als jullie Slack gebruiken | Laag |

### Project-specifieke meldingen (aanbevolen — hoge waarde)

Leg Today's projectlocaties vast en krijg een gerichte melding zodra er een
signaal over die locatie binnenkomt — bv. een **voorbereidingsbesluit** (dat
ontwikkeling kan bevriezen) in die buurt.

1. Lijst van projecten: gemeente + locatie-aanduidingen (naam, straat, wijk, kavel).
2. Bij elk nieuw signaal: juiste gemeente én noemt het de projectlocatie?
3. Zo ja → directe melding: "⚠️ Voorbereidingsbesluit nabij [project X] in [gemeente]".

| Niveau | Hoe | Haalbaarheid |
|---|---|---|
| A. Tekst-match | projectnaam/straat/wijk in de signaaltekst herkennen | Goed haalbaar |
| B. Geo-match | plangrenzen vergelijken met het perceel | Geavanceerd (geo-data) |

**Samenhang:** meldingen vereisen dat de pipeline automatisch draait (anders is
er niets nieuws om over te melden). De meldingen zelf zijn gratis; de kosten
zitten in de geplande pipeline-run.

---

## Continu monitoren (automatisch bijhouden)

Nu draait de pipeline **handmatig**. Voor automatisch bijhouden moet de pipeline
op een schema draaien én moeten de resultaten beschikbaar komen.

**Belangrijk:** Streamlit Cloud kan de pipeline zelf **niet** draaien (het toont
alleen het dashboard, en de opslag is tijdelijk). Het verzamelen gebeurt dus
ergens anders, waarna de bijgewerkte database online wordt gezet.

| Manier | Draait als pc uit is? | Kosten | Moeite | Past bij |
|---|---|---|---|---|
| Windows Taakplanner (eigen pc) | Nee | Gratis | Laag | snel starten, klein |
| GitHub Actions (cloud) | Ja | Gratis (binnen limieten) | Midden | huidige GitHub + Streamlit-opzet |
| Cloud-server (cron-job) | Ja | € per maand | Hoog | bedrijfsbreed / groot volume |

**Cadans:** dagelijks · **wekelijks (aanbevolen)** · maandelijks. Wekelijks is
meestal de juiste balans tussen actualiteit en kosten.

**Wat is automatisch actueel?**
- **Netcongestie:** altijd live — geen planning nodig.
- **Signalen (beleid):** vereisen geplande pipeline-runs.
- **Meldingen:** hangen af van die geplande runs.

**Kosten per run:** alleen *nieuwe* documenten worden geclassificeerd, dus een
geplande run is goedkoop (van een paar cent tot ~€0,50, afhankelijk van volume
en aantal gemeenten).

**Aanbevolen opzet:** GitHub Actions, wekelijks → de pipeline draait in de cloud,
zet de bijgewerkte database terug in GitHub, Streamlit werkt zich vanzelf bij, en
stuurt optioneel een melding bij nieuwe sterke risico's.

---

## Overige functies

- Kaartweergave (signalen op een kaart van Nederland).
- Markeren & notities (signalen afvinken, opmerkingen, status "opgevolgd").
- Gebruikersrollen (wie ziet/doet wat bij meerdere gebruikers).
- Volledige-tekst zoeken (documenttekst meeopslaan).
- Deduplicatie over bronnen heen (zelfde plan in twee bronnen samenvoegen).
- Grafieken & Excel/PDF-export.
- Engelstalige versie.

---

## Routekaart (gefaseerd)

- **Fase A — Verbreden & verdiepen:** provinciale bekendmakingen + netcongestie-
  kaart; eventueel zoekdiepte verhogen (semantisch of breed + AI-filter).
- **Fase B — Zuinig & schaalbaar maken:** Haiku + caching + Batch API.
- **Fase C — Gericht geografisch opschalen:** gemeentenlijst van Today's
  werkgebied → één grote run.
- **Fase D — Automatiseren & melden:** wekelijkse run + meldingen, inclusief de
  project-specifieke alerts.

---

## Kosten- en privacy-aandachtspunten

- De bronnen zijn grotendeels gratis; kosten zitten in de AI-classificatie.
- Stel een maandlimiet in op console.anthropic.com (Billing → Limits).
- De API-sleutel hoort in secrets, nooit in de code of op GitHub.
- De online versie is een etalage; verzamelen gebeurt waar de pipeline draait.
- Kadaster-eigendom en sommige geo-data zijn betaald of privacy-beperkt.
