# logic/parser.py
import re
from bs4 import BeautifulSoup
import requests
from data.models import AdInfo

def parse_ad(url: str = None, text: str = None) -> AdInfo:
    """
    Parse an advertisement either from a URL or from raw text.
    Returns an AdInfo object with title, price, location, and description.
    """
    # ---------- (1) Analyse per URL -----------------------------------------
    if url:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Titel
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        # Preis
        price = next((t.strip() for t in soup.stripped_strings if "€" in t), "")
        # Ort
        location = ""
        loc_match = soup.find(string=re.compile(r"^\d{4,5}\s"))
        if loc_match:
            location = loc_match.strip()
            location = re.sub(r"\s+\d{1,2}\.\d{1,2}\.\d{4}$", "", location)  # Datum entfernen
        # Beschreibung
        desc_container = soup.find(id="viewad-description") or soup.find("div", class_="AdDescription")
        description = desc_container.get_text(" ", strip=True) if desc_container else ""

        return AdInfo(title=title, price=price, location=location, description=description)

    # ---------- (2) Analyse per Freitext -----------------------------------
    elif text:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        title = lines[0] if lines else ""
        price = next((l for l in lines if "€" in l), "")
        location = next((l for l in lines if re.match(r"^\d{4,5}\s", l)), "")
        description = "\n".join(l for l in lines if l not in (title, price, location))
        return AdInfo(title=title, price=price, location=location, description=description)

    else:
        raise ValueError("parse_ad benötigt entweder url oder text.")

def parse_search_input(query: str) -> str:
    """
    Placeholder parser for hotel search queries.
    Currently returns the query unchanged. In the future, this could normalize or extract details.
    """
    # No special parsing at the moment
    return query

# Additional parsing functions can be added here as needed in the future.
