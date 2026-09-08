import json
import requests
from django.conf import settings


def ai_semantic_product_search(query, products_qs, limit=12):
    """
    Uses the Groq LLM to find products conceptually related to `query` even
    when no exact keyword matches — e.g. "something for a headache" should
    surface "Paracetamol" despite sharing no words with the product name.

    Returns a list of Product instances (possibly empty), most relevant first.
    Never raises — falls back to an empty list on any failure so a broken
    AI call never breaks the search page itself.
    """
    if not settings.AI_API_KEY:
        return []

    id_map = {}
    catalog_lines = []
    for product in products_qs.select_related('category')[:300]:
        id_map[product.id] = product
        line = f"{product.id}: {product.name} (category: {product.category.name})"
        if product.dosage:
            line += f" - {product.dosage}"
        catalog_lines.append(line)

    if not catalog_lines:
        return []

    system_prompt = (
        "You are a clinical pharmacy search assistant. Map user queries, symptoms, "
        "or colloquial health conditions (e.g., 'vomit', 'throwing up', 'nausea', 'headache') "
        "to relevant catalog products (e.g., anti-emetics, ORS/rehydration salts, antacids, digestive health, or general remedies).\n\n"
        "Respond with ONLY a JSON array of matching product ID integers, ordered by medical relevance.\n"
        "Do NOT include markdown fences, explanations, or text.\n"
        f"Return at most {limit} IDs. If no items in the catalog match even broadly, return []."
    )
    user_prompt = f"Query: {query}\n\nCatalog:\n" + "\n".join(catalog_lines)

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }

    try:
        response = requests.post(settings.AI_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        # Defensive: strip markdown fences in case the model adds them anyway
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:].strip()
        ids = json.loads(content)
        return [id_map[i] for i in ids if i in id_map][:limit]
    except Exception as e:
        print(f"--- AI SEARCH ERROR: {e} ---")
        return []