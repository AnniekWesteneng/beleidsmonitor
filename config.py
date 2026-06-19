# Gemeenten die we monitoren. Opschalen = deze lijst uitbreiden.
GEMEENTEN = [
    # Casusgemeenten
    "Den Haag", "Utrecht", "Almere",
    # Brabantse logistieke regio
    "Tilburg", "Waalwijk", "Moerdijk", "Breda", "Oosterhout",
    "Meierijstad", "Oss", "'s-Hertogenbosch", "Eindhoven", "Helmond",
]

# Provincies waarvan we ook het beleid meenemen (regionale programmering van
# bedrijventerreinen). Hoort logisch bij de gekozen gemeenten. Breid mee uit als
# je gemeenten toevoegt. Alleen de Officiële-Bekendmakingen-bron gebruikt deze.
PROVINCIES = ["Zuid-Holland", "Utrecht", "Flevoland", "Noord-Brabant"]

# De 10 beleidsindicatoren uit het onderzoek (bijlage 12/13)
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

# Zoektermen om relevante documenten te vinden, gericht op de 10 indicatoren.
# De volledige (uitgebreide) lijst staat in zoektermen.py — daar gegroepeerd
# per indicator. Pas die lijst aan om de zoekstap breder/smaller te maken.
from zoektermen import ZOEKTERMEN  # noqa: E402,F401

# Alleen documenten vanaf dit jaar meenemen. Oudere stukken (bv. 2010) zijn
# voor een actuele kans/risico-inschatting meestal niet relevant.
# Verlaag dit getal als je verder terug wilt kijken.
VANAF_JAAR = 2022

# Neem ook provinciaal/regionaal beleid mee (provincies programmeren veel
# bedrijventerreinen). Zet op False om strikt alleen gemeentelijk te blijven.
INCLUSIEF_PROVINCIE = True

# Maximaal aantal tekens dat per document naar het AI-model gaat. Bij langere
# documenten selecteren we slim de passages rond de zoekterm (zie verwerk.py).
# Hoger = vollediger maar duurder.
MAX_TEKST_TEKENS = 16000

# AI-model voor classificatie. Haiku = snel & goedkoop (~3x goedkoper dan Sonnet),
# ruim voldoende voor signaleren. Wil je diepere/genuanceerdere analyse?
# Zet op "claude-sonnet-4-6" (duurder).
CLASSIFICATIE_MODEL = "claude-haiku-4-5"

