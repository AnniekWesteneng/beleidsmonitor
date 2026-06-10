# Het dashboard online zetten (Streamlit Community Cloud)

Hiermee maak je het dashboard bereikbaar voor collega's via een vaste link,
beveiligd met een wachtwoord. Gratis. Reken op 20–30 minuten de eerste keer.

> **Belangrijk:** de API-sleutel en het wachtwoord komen NOOIT in de code of
> op GitHub. Die zet je apart in de "Secrets" van Streamlit Cloud (stap 4).

---

## Stap 1 — Zet de code op GitHub

De makkelijkste manier zonder commando's is **GitHub Desktop**:

1. Maak een gratis account op [github.com](https://github.com).
2. Download en installeer [GitHub Desktop](https://desktop.github.com/).
3. In GitHub Desktop: **File → Add local repository** → kies de map
   `beleidsmonitor`. (Is het nog geen repository? Klik op
   "create a repository" als dat wordt voorgesteld.)
4. Geef het een naam, bv. `beleidsmonitor`, en zet 'm op **Private**
   (privé — alleen jij en wie je uitnodigt kunnen de code zien).
5. Klik **Commit to main** en daarna **Publish repository**.

Wat wél meegaat: de code en `beleidsmonitor.db` (de data).
Wat NIET meegaat (staat in `.gitignore`): `.env` en `secrets.toml` — je geheimen.

## Stap 2 — Koppel Streamlit Cloud aan GitHub

1. Ga naar [share.streamlit.io](https://share.streamlit.io) en log in **met je
   GitHub-account**.
2. Klik **Create app** → **Deploy a public app from GitHub** (de app zelf maken
   we privé met een wachtwoord).

## Stap 3 — Kies de app

- **Repository:** `<jouw-gebruikersnaam>/beleidsmonitor`
- **Branch:** `main`
- **Main file path:** `dashboard.py`
- Klik **Deploy**.

De eerste keer duurt het installeren een paar minuten.

## Stap 4 — Zet de geheimen (wachtwoord + API-sleutel)

1. In je app op Streamlit Cloud: **Settings (⋮) → Secrets**.
2. Plak hierin (vul je eigen waarden in):

   ```toml
   app_wachtwoord = "kies-een-sterk-wachtwoord"
   ANTHROPIC_API_KEY = "sk-ant-...jouw-sleutel..."
   ```

3. Opslaan. De app herstart automatisch.

Klaar! Deel de app-link + het wachtwoord met je collega's.

---

## Bijwerken met nieuwe data

De online versie toont de data uit `beleidsmonitor.db` op het moment van
publiceren. Wil je nieuwe signalen online?

1. Draai lokaal de pipeline (`python pipeline.py`) — dat vult de database bij.
2. In GitHub Desktop: **Commit** de gewijzigde `beleidsmonitor.db` en **Push**.
3. Streamlit Cloud werkt vanzelf bij.

> De pipeline draait dus **lokaal** (op jouw pc, met API-tegoed). De online
> versie is een leesbare etalage + chat.

## Kosten in de gaten houden

- De **chat** kost API-tegoed per vraag — voor álle gebruikers samen.
- Stel een **maandlimiet** in op [console.anthropic.com](https://console.anthropic.com)
  (Billing → Limits) zodat je nooit voor verrassingen komt te staan.
- Wil je de chat in de online versie liever uitzetten? Vraag me dat, dan maak
  ik 'm afschakelbaar.
