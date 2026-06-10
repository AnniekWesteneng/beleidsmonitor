"""Draai de pipeline voor een beperkte subset (testen / kostenbeheer).

Gebruikt ALLE gekoppelde bronnen, maar met minder gemeenten/zoektermen.
Pas de lijsten hieronder aan om meer/minder te verzamelen.

Draaien:  python run_subset.py
"""
from pipeline import run

GEMEENTEN = ["Den Haag", "Utrecht", "Almere"]
ZOEKTERMEN = ["bedrijventerrein", "werklocatie"]
MAX_PER_TERM = 5

if __name__ == "__main__":
    run(gemeenten=GEMEENTEN, zoektermen=ZOEKTERMEN, max_per_term=MAX_PER_TERM)
