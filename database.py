"""Laag 4 — Opslaan: resultaten in een SQLite-database.

Eén bestand (beleidsmonitor.db), geen server nodig.

Een document kan MEERDERE signalen opleveren (één per geraakte indicator),
dus de uniciteit ligt op de combinatie (url, indicator_id) i.p.v. alleen url.
Zo voorkomen we dubbele rijen én kunnen we toch meerdere indicatoren per
document opslaan.
"""
import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).resolve().parent / "beleidsmonitor.db")

# Nieuw schema: url is NIET meer kolom-uniek (uniciteit via samengestelde index).
_CREATE = """
    CREATE TABLE IF NOT EXISTS signalen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gemeente TEXT, titel TEXT, documenttype TEXT, bron TEXT,
        datum TEXT, url TEXT,
        indicator_id INTEGER, classificatie TEXT, relevantie INTEGER,
        status TEXT, eigenaar TEXT, grondpositie TEXT,
        samenvatting TEXT, onderbouwing TEXT, citaat TEXT, pagina INTEGER,
        opgehaald_op TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""

_NIEUWE_KOLOMMEN = [
    "id", "gemeente", "titel", "documenttype", "bron", "datum", "url",
    "indicator_id", "classificatie", "relevantie", "status", "eigenaar",
    "grondpositie", "samenvatting", "onderbouwing", "citaat", "pagina", "opgehaald_op",
]


def _migreer_van_url_unique(conn: sqlite3.Connection) -> None:
    """Zet een oude tabel met 'url TEXT UNIQUE' om naar het nieuwe schema,
    met behoud van bestaande rijen."""
    conn.execute("ALTER TABLE signalen RENAME TO signalen_oud")
    conn.execute(_CREATE)
    oud_kolommen = [r[1] for r in conn.execute("PRAGMA table_info(signalen_oud)").fetchall()]
    gemeenschappelijk = [k for k in _NIEUWE_KOLOMMEN if k in oud_kolommen]
    cols = ", ".join(gemeenschappelijk)
    conn.execute(f"INSERT INTO signalen ({cols}) SELECT {cols} FROM signalen_oud")
    conn.execute("DROP TABLE signalen_oud")
    conn.commit()
    print("Database gemigreerd: meerdere indicatoren per document nu mogelijk.")


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE)

    # Migratie 1: oud schema met 'url TEXT UNIQUE' -> nieuw schema.
    rij = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='signalen'"
    ).fetchone()
    if rij and "url TEXT UNIQUE" in rij[0]:
        _migreer_van_url_unique(conn)

    # Migratie 2: zorg dat de kolommen relevantie/citaat/pagina bestaan (oudere DBs).
    kolommen = [r[1] for r in conn.execute("PRAGMA table_info(signalen)").fetchall()]
    if "relevantie" not in kolommen:
        conn.execute("ALTER TABLE signalen ADD COLUMN relevantie INTEGER")
    if "citaat" not in kolommen:
        conn.execute("ALTER TABLE signalen ADD COLUMN citaat TEXT")
    if "pagina" not in kolommen:
        conn.execute("ALTER TABLE signalen ADD COLUMN pagina INTEGER")
    # Migratie 3: context-velden status/eigenaar/grondpositie.
    for _k in ("status", "eigenaar", "grondpositie"):
        if _k not in kolommen:
            conn.execute(f"ALTER TABLE signalen ADD COLUMN {_k} TEXT")

    # Uniciteit op (url, indicator_id): geen dubbele signalen, wel meerdere
    # indicatoren per document.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_url_indicator "
        "ON signalen(url, indicator_id)"
    )
    conn.commit()
    return conn


def url_bestaat(conn: sqlite3.Connection, url: str) -> bool:
    """Is dit document al verwerkt (geclassificeerd)? Zo ja, dan slaan we de
    (dure) classificatie over."""
    if not url:
        return False
    cur = conn.execute("SELECT 1 FROM signalen WHERE url = ? LIMIT 1", (url,))
    return cur.fetchone() is not None


def sla_op(conn: sqlite3.Connection, signaal: dict) -> None:
    try:
        conn.execute("""INSERT OR IGNORE INTO signalen
            (gemeente, titel, documenttype, bron, datum, url,
             indicator_id, classificatie, relevantie, status, eigenaar, grondpositie,
             samenvatting, onderbouwing, citaat, pagina)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (signaal.get("gemeente"), signaal.get("titel"), signaal.get("documenttype"),
             signaal.get("bron"), signaal.get("datum"), signaal.get("url"),
             signaal.get("indicator_id"), signaal.get("classificatie"),
             signaal.get("relevantie"), signaal.get("status"), signaal.get("eigenaar"),
             signaal.get("grondpositie"),
             signaal.get("samenvatting"), signaal.get("onderbouwing"),
             signaal.get("citaat"), signaal.get("pagina")))
        conn.commit()
    except Exception as e:
        print(f"Opslaan mislukt: {e}")
