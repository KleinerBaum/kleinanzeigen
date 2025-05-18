from dataclasses import dataclass, field, asdict
from typing import List, Dict

@dataclass
class AdInfo:
    title: str = ""
    price: str = ""
    location: str = ""
    description: str = ""
    image_urls: List[str] = field(default_factory=list)
    contact_info: Dict[str, str] = field(default_factory=dict)
    url: str = ""

    def to_dict(self):
        return asdict(self)

    def as_markdown(self) -> str:
        # Übersichtliche Ausgabe für Streamlit etc.
        md = f"### {self.title}\n\n"
        if self.price:
            md += f"**Preis:** {self.price}\n\n"
        if self.location:
            md += f"**Ort:** {self.location}\n\n"
        if self.description:
            md += f"**Beschreibung:**\n{self.description}\n\n"
        if self.image_urls:
            md += f"**Bilder:**\n" + "\n".join(self.image_urls) + "\n"
        if self.contact_info:
            md += f"**Kontakt:**\n"
            for k, v in self.contact_info.items():
                md += f"- {k}: {v}\n"
        if self.url:
            md += f"\n[Zur Anzeige]({self.url})"
        return md
