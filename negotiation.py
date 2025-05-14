import openai

def generate_personal_message(info, purposes, model="gpt-3.5-turbo"):
    introduction = (
        f"Sehr geehrte/r {info.get('seller_name')},\n\n"
        f"ich bin Gabi und zusammen mit meinem Freund auf Deutschlandtour. "
        f"Wir richten uns neu ein und da ist uns '{info.get('title')}' aufgefallen.\n\n"
    )

    text_parts = {
        "Erstkontakt": "Ist der Artikel noch verfügbar?",
        "Preisverhandlung": "Wäre eine Preisanpassung möglich?",
        "Zustandsabfrage": "Könnten Sie den Zustand näher beschreiben?",
        "Terminvereinbarung": f"Könnten wir einen Termin in {info.get('location')} vereinbaren?"
    }
    # Falls Preis verfügbar, Preisverhandlungs-Text verfeinern
    price_str = info.get('price')
    if price_str and price_str not in ["Nicht gefunden", ""]:
        import re
        match = re.search(r"\d+", price_str.replace('.', '').replace(',', ''))
        if match:
            orig_price = int(match.group(0))
            if orig_price > 0:
                proposed_price = int(min(orig_price * 0.8, orig_price - 1))
                base_price = price_str if '€' in price_str else f"{price_str} €"
                text_parts["Preisverhandlung"] = (
                    f"Ihre Preisvorstellung von {base_price} erscheint mir etwas hoch. "
                    f"Wären Sie zu einer Anpassung auf {proposed_price}€ bereit?"
                )

    body = "\n".join([text_parts[p] for p in purposes if p in text_parts])
    prompt = f"{introduction}\n{body}"
    # Anfrage an OpenAI senden
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        top_p=0.9
    )
    content = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {})
    return content, usage
