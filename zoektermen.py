"""Uitgebreide zoektermenlijst, gegroepeerd per indicator.

Samengesteld uit de handmatige kernlijst + door Claude voorgestelde synoniemen
en vakjargon (zie genereer_zoektermen.py). Een paar te generieke termen zijn
bewust weggelaten om te voorkomen dat irrelevante documenten binnenstromen.

LET OP: deze lijst telt veel termen. Het aantal termen kost niets; alleen het
DRAAIEN ervan kost tijd/API-calls (per term x gemeente x bron). Gebruik voor
testruns gerust een subset (zie run_subset.py).
"""

ZOEKTERMEN = [
    # Algemeen / kern
    "bedrijventerrein", "werklocatie", "bedrijvenpark",

    # Bedrijfshuisvesting / verzamelgebouwen (Today-product; indicator 2 en 8)
    "bedrijfsverzamelgebouw", "bedrijfsverzamelpand", "bedrijfsverzamelcentrum",
    "verzamelgebouw", "bedrijfsunit", "logistiek vastgoed",

    # 1. Transformatiedruk op industriële bestemming
    "transformatie", "herbestemming", "transformatiegebied",
    "woningbouwlocatie", "functiemenging", "stedelijke verdichting",
    "herontwikkeling bedrijventerrein", "wonen-werken", "woonmilieu",

    # 2. Beschikbaarheid en programmering bedrijventerrein
    "uitgeefbaar terrein", "bedrijventerreinprogrammering", "restcapaciteit",
    "kavelbeschikbaarheid", "terreincapaciteit", "bedrijfsruimte behoefte",
    "regionaal werkprogramma",

    # 3. Milieuruimte en milieuzonering
    "milieuzonering", "milieucategorie", "geluidzone", "hindercontour",
    "VNG-categorieën", "geluidszone industrielawaai", "bedrijfscategorie",
    "richtafstand", "geurcontour",

    # 4. Energie-infrastructuur en netcongestie
    "netcongestie", "transformatorstation", "energie-infrastructuur",
    "transportcapaciteit", "verzwaring elektriciteitsnet", "aansluittermijn",
    "transportverzoek", "congestiegebied", "netverzwaring",
    "grootverbruikersaansluiting",

    # 5. Infrastructuur en logistieke bereikbaarheid
    "ontsluiting", "logistiek", "verkeersbesluit", "ontsluiting vrachtverkeer",
    "havengebonden", "multimodaal knooppunt", "wegcategorisering",
    "logistieke corridor", "achterlandverbinding", "spoorontsluiting",

    # 6. Eigendomsstructuur en grondpositie
    "grondexploitatie", "erfpacht", "gronduitgifte", "gemeentelijke grondpositie",
    "erfpachtcanon", "anterieure overeenkomst", "actieve grondpolitiek",
    "verwervingsstrategie", "minnelijke verwerving",

    # 7. Bouwregelgeving en exploitatierandvoorwaarden
    "exploitatieplan", "bouwvolume", "bebouwingspercentage", "bouwhoogte maximaal",
    "parkeernorm", "uitgeefbare grond", "bouwregels bestemmingsplan",
    "stedenbouwkundig kader",

    # 8. Functieverruiming op bestaande locatie
    "functieverruiming", "binnenplanse afwijking", "functiewijziging",
    "afwijkingsbevoegdheid", "gebruikswijziging", "planologische medewerking",
    "uitbreiding gebruiksmogelijkheden", "bestemmingswijziging",
    "omgevingsplanactiviteit",

    # 9. Actief vestigingsbeleid en economische stimulering
    "vestigingsbeleid", "economische visie", "vestigingsklimaat",
    "acquisitiebeleid", "economische structuurversterking",
    "bedrijfshuisvestingsvraag", "acquisitiedoelstelling",

    # 10. Vergunningstraject als projectrisico
    "omgevingsvergunning", "maatwerkvoorschrift", "doorlooptijd vergunning",
    "omgevingsvergunning verlening", "zienswijzeprocedure", "beroepsprocedure",
    "coördinatiebesluit", "vergunningplichtig", "Wabo-procedure", "bezwaartermijn",

    # Aanvullend planologisch
    "omgevingsplan", "bestemmingsplan", "voorbereidingsbesluit",
    "uitgifte bedrijfskavel",
]
