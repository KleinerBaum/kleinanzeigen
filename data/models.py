"""
Optionales Datenmodell:
Hier könntest du eine einfache Dataklasse definieren,
wenn du an manchen Stellen strukturierte Objekte verwenden willst.
"""

class AdInfo:
    def __init__(self, title: str = "", price: str = "", description: str = ""):
        self.title = title
        self.price = price
        self.description = description

    def __repr__(self):
        return f"<AdInfo title='{self.title}', price='{self.price}'>"
