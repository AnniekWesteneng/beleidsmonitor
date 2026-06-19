"""Verifieer (gratis) of nieuwe gemeentenamen data teruggeven in beide bronnen."""
from bronnen.officiele_bekendmakingen import haal as ob_haal
from bronnen.open_raadsinformatie import haal as ori_haal, _index_voor

GEMEENTEN = ["Tilburg", "Waalwijk", "Moerdijk", "Breda", "Oosterhout",
             "Meierijstad", "Oss", "'s-Hertogenbosch", "Eindhoven", "Helmond"]

print(f"{'gemeente':<20} {'SRU':>5} {'ORI':>5}   ORI-index")
for g in GEMEENTEN:
    try:
        sru = len(ob_haal(g, "bedrijventerrein", 5))
    except Exception as e:
        sru = f"FOUT({type(e).__name__})"
    try:
        ori = len(ori_haal(g, "bedrijventerrein", 5))
    except Exception as e:
        ori = f"FOUT({type(e).__name__})"
    print(f"{g:<20} {str(sru):>5} {str(ori):>5}   {_index_voor(g)}")
