# Daten-Klassen für Kleinanzeigen (z.B. von parser.py genutzt)

# Hinweis: Nutzung von @dataclass entfernt, um flexible Initialisierung zu ermöglichen.
# Klasse repräsentiert die wichtigsten Felder einer Kleinanzeige.
class AdInfo:
    def __init__(self, title: str = "", price: str = "", location: str = "", description: str = ""):
        self.title = title
        self.price = price
        self.location = location
        self.description = description

    def __repr__(self):
        return f"<AdInfo title='{self.title}', price='{self.price}'>"
