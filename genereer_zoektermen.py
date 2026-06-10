"""Query-expansie: laat Claude per indicator extra zoektermen voorstellen.

Doel: de zoekstap (die letterlijk op trefwoorden matcht) breder maken, zodat
minder relevante documenten gemist worden. Draai dit eenmalig, bekijk de
voorgestelde lijst, en neem de bruikbare termen over in config.py.

Draaien:  python genereer_zoektermen.py
"""
import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from config import INDICATOREN, ZOEKTERMEN

load_dotenv()
MODEL = "claude-sonnet-4-6"

indicator_lijst = "\n".join(f'{i["id"]}. {i["naam"]}' for i in INDICATOREN)

PROMPT = f"""Je helpt bij het bouwen van een zoekmachine voor Nederlandse gemeentelijke
en provinciale beleidsdocumenten, voor een ontwikkelaar van industrieel vastgoed.

De zoekstap matcht LETTERLIJK op trefwoorden. Geef per onderstaande indicator 6-8
Nederlandse zoektermen (losse woorden of korte woordcombinaties) die daadwerkelijk
in zulke beleidsdocumenten voorkomen en deze indicator signaleren. Denk aan
vakjargon, synoniemen en gerelateerde begrippen.

EISEN:
- Specifiek genoeg om relevante documenten te vinden, maar niet zo algemeen dat
  alles matcht (vermijd 'beleid', 'gemeente', 'plan', 'besluit').
- Termen die echt in officiele stukken/omgevingsplannen/raadsstukken voorkomen.
- Geen dubbele termen tussen indicatoren.

De 10 indicatoren:
{indicator_lijst}

Antwoord UITSLUITEND met JSON: een object met indicator-id (als string) -> lijst van termen.
Bijvoorbeeld: {{"1": ["herbestemming", "woningbouwlocatie", ...], "2": [...], ...}}"""


def main():
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    bericht = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": PROMPT}],
    )
    tekst = bericht.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    per_indicator = json.loads(tekst)

    print("=== Voorgestelde termen per indicator ===")
    nieuwe = []
    for i in INDICATOREN:
        termen = per_indicator.get(str(i["id"]), [])
        print(f'\n{i["id"]}. {i["naam"]}')
        print("   " + ", ".join(termen))
        nieuwe.extend(termen)

    # Samenvoegen met de bestaande lijst, dedupliceren (hoofdletterongevoelig).
    samen = list(ZOEKTERMEN) + nieuwe
    gezien, uniek = set(), []
    for t in samen:
        sleutel = t.lower().strip()
        if sleutel and sleutel not in gezien:
            gezien.add(sleutel)
            uniek.append(t.strip())

    print(f"\n\n=== SAMENGEVOEGDE LIJST ({len(uniek)} unieke termen) ===")
    print("ZOEKTERMEN = [")
    for t in uniek:
        print(f'    "{t}",')
    print("]")


if __name__ == "__main__":
    main()
