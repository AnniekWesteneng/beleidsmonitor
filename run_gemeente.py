"""Gerichte run van de volledige pipeline (beide bronnen) voor één of meer
gemeenten, eventueel met een provincie erbij.

Houdt runs kort (per gemeente) i.v.m. de ~20-min-limiet; dedup maakt herhalen
veilig. Provincie meegeven met prefix 'prov:'.

Gebruik:  python run_gemeente.py Zoetermeer
          python run_gemeente.py Hilversum prov:Noord-Holland
"""
import sys

from pipeline import run

if __name__ == "__main__":
    gemeenten, provincies = [], []
    for a in sys.argv[1:]:
        (provincies if a.startswith("prov:") else gemeenten).append(
            a[5:] if a.startswith("prov:") else a)
    if not gemeenten:
        print("Geef minstens één gemeente op.")
        sys.exit(1)
    run(gemeenten=gemeenten, provincies=provincies)
