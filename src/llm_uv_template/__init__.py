"""Euro-FH messenger PoC package."""

from llm_uv_template.agent import build_agent
from llm_uv_template.models import (
    GenerierteNachricht,
    NachrichtAnfrage,
    NachrichtAntwort,
    NachrichtTrigger,
    Studi,
    Tonalitaet,
)

__all__ = [
    "GenerierteNachricht",
    "NachrichtAnfrage",
    "NachrichtAntwort",
    "NachrichtTrigger",
    "Studi",
    "Tonalitaet",
    "build_agent",
]
__version__ = "0.1.0"
