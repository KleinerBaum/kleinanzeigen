from dataclasses import dataclass

@dataclass
class AdInfo:
    """Datenstruktur für extrahierte Anzeigeninformationen."""
    title: str
    price: str
    location: str
    description: str = ""
