"""Chat met de beleidsmonitor: beantwoord vragen op basis van de signalen.

Het zware denkwerk (classificatie) is al gedaan; deze module geeft alleen
antwoord op basis van de signalen die we aanreiken. Daarom volstaat een
goedkoop model (Haiku) prima.
"""
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Keuzemenu in het dashboard. Sleutel = label, waarde = model-id.
MODELLEN = {
    "Haiku — snel & goedkoop (aanbevolen)": "claude-haiku-4-5",
    "Sonnet — scherper & duurder": "claude-sonnet-4-6",
}

SYSTEEM = """Je bent een feitelijke beleidsanalist voor Today Development, ontwikkelaar
van industrieel vastgoed. Je beantwoordt vragen UITSLUITEND op basis van de hieronder
aangeleverde beleidssignalen. Regels:
- Baseer je antwoord alleen op de aangeleverde signalen; verzin niets.
- Verwijs concreet naar gemeente en indicator waar relevant.
- Als het antwoord niet uit de signalen blijkt, zeg dat dan eerlijk.
- Antwoord beknopt en in het Nederlands.

OPMAAK (belangrijk, houd het professioneel en compact):
- Gebruik GEEN markdown-koppen (geen #, ##, ###) en GEEN grote titel.
- Begin direct met 1-2 zinnen kernantwoord.
- Gebruik daarna waar nuttig een korte opsomming met bullets (-).
- Markeer een kort label vetgedrukt met **dubbele sterren**, gevolgd door een
  dubbele punt en de toelichting op dezelfde regel (bv. "**Risico:** ...").
- Houd alinea's kort (max ~3 regels). Geen overbodige inleiding of afsluiting."""

_client = None


def _client_get() -> Anthropic:
    global _client
    if _client is None:
        sleutel = os.environ.get("ANTHROPIC_API_KEY", "")
        if not sleutel or sleutel.startswith("sk-ant-..."):
            raise RuntimeError("Geen geldige ANTHROPIC_API_KEY in .env.")
        _client = Anthropic(api_key=sleutel)
    return _client


def beantwoord_vraag(vraag: str, signalen_context: str, model: str) -> str:
    """Stel de vraag aan het model met de signalen als context."""
    inhoud = (
        f"Hier zijn de relevante beleidssignalen:\n\n{signalen_context}\n\n"
        f"Vraag: {vraag}"
    )
    bericht = _client_get().messages.create(
        model=model,
        max_tokens=1000,
        system=SYSTEEM,
        messages=[{"role": "user", "content": inhoud}],
    )
    return bericht.content[0].text.strip()
